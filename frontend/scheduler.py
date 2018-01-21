"""
This module contains a scheduler which runs programs on the different clients.
"""

from threading import Timer
import threading

import logging
from server.utils import notify

LOGGER = logging.getLogger("scheduler")


class SchedulerStatus:
    """
    This class defines the different Scheduler states.

    INIT
    ----
        The scheduler starts all relevant slaves

    WAITING_FOR_SLAVES
    ------------------
        The scheduler waits for all slaves to connect to the master.

    NEXT_STEP
    ---------
        The scheduler fetches the next index and executes the right programs.

    WAITING_FOR_PROGRAMS
    --------------------
        The scheduler waits for all programs to finish.

    SUCCESS
    -------
        The scheduler is in the end state and was successful.

    ERROR
    -----
        The scheduler is in the end state and was NOT successful.

    """
    INIT = 0
    WAITING_FOR_SLAVES = 1
    NEXT_STEP = 2
    WAITING_FOR_PROGRAMS = 3
    SUCCESS = 4
    ERROR = 5


class Scheduler:
    """
    A thread-safe scheduler which starts programs from a slave.
    """

    def __init__(self):
        self.event = threading.Event()
        self.lock = threading.Lock()

        self.__thread = None
        self.__error_code = None
        self.__stop = False
        self.__state = SchedulerStatus.INIT
        self.__index = -1
        self.__script = None

    def is_running(self):
        """
        This function is thread-safe.

        Returns if the underlying thread is still running.

        Returns
        -------
            bool
        """
        self.lock.acquire()

        if self.__thread is not None:
            alive = self.__thread.is_alive()
            LOGGER.debug(
                "Thread is %s",
                "online" if alive else "offline",
            )
        else:
            LOGGER.debug("Thread is offline")
            alive = False
        self.lock.release()
        return alive

    def should_stop(self):
        """
        This function is thread-safe.

        Returns if the underlying thread should stop.

        Returns
        -------
            bool
        """
        self.lock.acquire()
        stop = self.__stop
        self.lock.release()
        return stop

    def stop(self):
        """
        This function is thread-safe.

        Stops the scheduler and his thread.
        """
        self.lock.acquire()
        self.__stop = True
        self.event.set()

        if self.__thread is not None:
            self.__thread.join(timeout=2)

        self.lock.release()

    def start(self, script):
        """
        This function is thread-safe.

        Starts a new thread with and execute the given script. If a thread is
        already active this function will return False.

        Arguments
        ---------
            script: Identifier for ScriptModel

        Returns
        -------
            Returns true if the new thread was started.
        """
        if self.is_running():
            return False
        else:
            from .models import Script
            self.lock.acquire()

            self.__error_code = None
            self.__stop = False
            self.__state = SchedulerStatus.INIT
            self.__index = -1
            self.__script = script

            self.__thread = threading.Thread(
                daemon=True,
                target=self.__run__,
            )

            Script.objects.filter(id=self.__script).update(
                is_running=True,
                is_initialized=True,
                current_index=-1,
            )

            self.__thread.start()
            self.lock.release()
            return True

    def notify(self):
        """
        This function is thread-safe.

        Notifies the scheduler that something has changed. That means the
        scheduler will look at the data again.
        """
        running = self.is_running()
        self.lock.acquire()
        if running and not self.event.is_set():
            self.event.set()
        self.lock.release()

    def __next_stage(self):
        """
        Generates the next stage and returns the number of the last stage and
        if this stage is valid.

        Returns
        --------
            last index and if this stage is valid

        """
        from .models import ScriptGraphPrograms

        old_index = self.__index

        try:
            query = ScriptGraphPrograms.objects.filter(
                script=self.__script,
                index__gt=self.__index,
            ).order_by('index')

            self.__index = query[0].index
            LOGGER.debug("Scheduler found next index %s", self.__index)
            all_done = False
        except IndexError:
            LOGGER.debug("Scheduler done")
            self.__index += 1
            all_done = True

        return (old_index, all_done)

    def timer_scheduler_slave_timeout(self):
        """
        Callback function for slave timeout.

        Arguments
        ---------
            scheduler: SchedulerStatus object
        """
        self.lock.acquire()
        if self.__state == SchedulerStatus.WAITING_FOR_SLAVES:
            LOGGER.debug("Scheduler for slaves timeouted")
            self.__error_code = 'Not all slaves connected within 5 minutes.'
            self.__state = SchedulerStatus.ERROR
            self.event.set()

        self.lock.release()

    def __run__(self):
        """
        Function wich will be executed by the Thread.
        """

        while self.event.wait():
            self.event.clear()

            if self.__stop:
                LOGGER.info("Exit thread -> should_stop() == True")
                return

            self.lock.acquire()
            LOGGER.debug("Current state: %s", self.__state)

            if self.__state == SchedulerStatus.INIT:
                self.__state_init()

            elif self.__state == SchedulerStatus.WAITING_FOR_SLAVES:
                self.__state_wait_slaves()

            elif self.__state == SchedulerStatus.NEXT_STEP:
                self.__state_next()

            elif self.__state == SchedulerStatus.WAITING_FOR_PROGRAMS:
                self.__state_wait_programs()

            elif self.__state == SchedulerStatus.SUCCESS:
                self.__state_success()
                self.lock.release()
                return

            elif self.__state == SchedulerStatus.ERROR:
                self.__state_error()
                self.lock.release()
                return

            self.lock.release()

    def __state_init(self):
        """
        In this state all slaves are started.
        """
        from .models import Script, Slave

        for slave in Script.get_involved_slaves(self.__script):
            LOGGER.debug("Starting slave `%s`", slave)
            Slave.wake_on_lan(slave)

        self.__state = SchedulerStatus.WAITING_FOR_SLAVES
        self.event.set()

        timer = Timer(
            300.0,
            self.timer_scheduler_slave_timeout,
        )
        timer.daemon = True
        timer.start()

        notify({
            'script_status': 'waiting_for_slaves',
            'script_id': self.__script,
        })

    def __state_wait_slaves(self):
        """
        In this state the scheduler waits for all needed slaves to start.
        """
        from .models import Script

        if Script.check_online(self.__script):
            LOGGER.info("All slaves online")
            self.__state = SchedulerStatus.NEXT_STEP
            self.event.set()
        else:
            LOGGER.info("Waiting for all slaves to be online.")

    def __state_next(self):
        """
        In this state the next index is selected and the programs are started.
        """
        from .models import (
            Script,
            ScriptGraphPrograms,
            ScriptGraphFiles,
        )

        LOGGER.info(
            "Starting program for stage %s",
            self.__index,
        )

        (last_index, all_done) = self.__next_stage()
        max_start_time = 0

        Script.objects.filter(id=self.__script).update(
            current_index=self.__index)

        if all_done:
            LOGGER.info("Everything done ... scheduler done")
            self.__state = SchedulerStatus.SUCCESS
            self.event.set()

        else:
            self.__state = SchedulerStatus.WAITING_FOR_PROGRAMS

            for sgp in ScriptGraphPrograms.objects.filter(
                    script=self.__script,
                    index=self.__index,
            ):
                if max_start_time < sgp.program.start_time:
                    max_start_time = sgp.program.start_time
                sgp.program.enable()

        notify({
            'script_status': 'next_step',
            'index': self.__index,
            'last_index': last_index,
            'start_time': max_start_time,
            'script_id': self.__script,
        })

    def __state_wait_programs(self):
        """
        In this state the scheduler waits for all started programs to finish.
        """
        from .models import (
            ScriptGraphPrograms,
            ScriptGraphFiles,
        )

        progs = ScriptGraphPrograms.objects.filter(
            script=self.__script,
            index=self.__index,
        )

        step = True

        for sgp in progs:
            prog = sgp.program

            if prog.is_error:
                LOGGER.debug("Error in program %s", prog.name)
                self.__state = SchedulerStatus.ERROR
                self.__error_code = "Program {} has an error.".format(
                    prog.name)
                step = False
                self.event.set()

                break

            elif prog.is_running and not prog.is_timeouted:
                LOGGER.debug(
                    "Program %s is not ready yet.",
                    prog.name,
                )
                step = False

                break

        if step:
            self.__state = SchedulerStatus.NEXT_STEP
            self.event.set()
        else:
            LOGGER.info("Not all programs are finished.")

    def __state_success(self):
        """
        In this state the scheduler clean up and save the results.
        """
        from .models import Script

        LOGGER.info("Scheduler is already finished. (SUCCESS)")

        notify({
            'script_status': 'success',
            'script_id': self.__script,
        })

        Script.objects.filter(id=self.__script).update(
            is_running=False,
            error_code='',
        )

        Script.set_last_started(self.__script)

    def __state_error(self):
        """
        In this state the scheduler clean up and save the results.
        """
        from .models import Script

        LOGGER.info("Scheduler is already finished. (ERROR)")

        Script.objects.filter(id=self.__script).update(
            is_running=False,
            error_code=self.__error_code,
        )

        notify({
            'script_status': 'error',
            'error_code': self.__error_code,
            'script_id': self.__script,
        })
