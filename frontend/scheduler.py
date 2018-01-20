from threading import Timer
import threading

import logging
from server.utils import notify, notify_err

logger = logging.getLogger("scheduler")


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

        if self.__thread != None:
            logger.debug("Thread information: {}".format(
                self.__thread.name,
                self.__thread.ident,
            ))

            alive = self.__thread.is_alive()
            logger.debug(
                "Thread is {}".format("online" if alive else "offline"))
        else:
            logger.debug("Thread is offline")
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

            db_obj = Script.objects.get(id=self.__script)
            db_obj.is_running = True
            db_obj.is_initialized = True
            db_obj.current_index = -1
            db_obj.save()

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
        Generates the next stage and returns the number of the last stage and if
        this stage is valid.

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
            logger.debug("Scheduler found next index " + str(self.__index))
            all_done = False
        except IndexError:
            logger.debug("Scheduler done")
            self.__index = -1
            all_done = True

        return (old_index, all_done)

    def timer_scheduler_slave_timeout(self):
        """
        Callback function for slave timeout.

        Arguments
        ---------
            scheduler: SchedulerStatus object
        """
        from .models import Script

        logger.debug("Scheduler for slaves timeouted")

        db_obj = Script.objects.get(id=self.__script)
        db_obj.error_code = 'Not all slaves connected within 5 minutes.'
        db_obj.is_running = False
        db_obj.save()

        self.lock.acquire()
        self.__error_code = 'Not all slaves connected within 5 minutes.'
        self.__state = SchedulerStatus.ERROR
        self.lock.release()
        self.event.set()

    def __run__(self):
        """
        Function wich will be executed by the Thread.
        """
        from .models import (
            Slave,
            Script,
            ScriptGraphPrograms,
            ScriptGraphFiles,
            Program,
            File,
        )

        while self.event.wait():
            self.event.clear()

            if self.should_stop():
                return

            self.lock.acquire()
            logger.debug("Current state: {}".format(self.__state))

            if self.__state == SchedulerStatus.INIT:
                for slave in Script.objects.get(
                        id=self.__script).get_involved_slaves():
                    logger.debug("Starting slave `{}`".format(slave.name))
                    slave.wake_on_lan()

                self.__state = SchedulerStatus.WAITING_FOR_SLAVES
                self.event.set()

                Timer(
                    300.0,
                    self.timer_scheduler_slave_timeout,
                ).start()

                notify({
                    'script_status': 'waiting_for_slaves',
                    'script_id': self.__script,
                })

            elif self.__state == SchedulerStatus.WAITING_FOR_SLAVES:
                if Script.objects.get(id=self.__script).check_online():
                    logger.info("All slaves online")
                    self.__state = SchedulerStatus.NEXT_STEP
                    self.event.set()
                else:
                    logger.info("Waiting for all slaves to be online.")

            elif self.__state == SchedulerStatus.NEXT_STEP:
                logger.info("Starting program for stage {}".format(
                    self.__index))

                (last_index, all_done) = self.__next_stage()

                if all_done:
                    logger.info("Everything done ... scheduler done")
                    self.__state = SchedulerStatus.SUCCESS
                    self.event.set()

                else:
                    self.__state = SchedulerStatus.WAITING_FOR_PROGRAMS

                    max_start_time = 0

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

            elif self.__state == SchedulerStatus.WAITING_FOR_PROGRAMS:
                logger.info("Waiting for programs to finish")

                progs = ScriptGraphPrograms.objects.filter(
                    script=self.__script,
                    index=self.__index,
                )

                step = True if len(progs) > 0 else False

                for sgp in progs:
                    prog = sgp.program
                    if prog.is_error:
                        logger.debug("Error in program {}".format(prog.name))
                        self.__state = SchedulerStatus.ERROR
                        self.__error_code = "Program {} has an error.".format(
                            prog.name)
                        step = False
                        self.event.set()

                        break
                    elif prog.is_running and not prog.is_timeouted:
                        logger.debug("Program {} is not ready yet.".format(
                            prog.name))
                        step = False

                        break
                if step:
                    self.__state = SchedulerStatus.NEXT_STEP
                    self.event.set()
                else:
                    logger.info("Not all programs are finished.")

            elif self.__state == SchedulerStatus.SUCCESS:
                logger.info("Scheduler is already finished. (SUCCESS)")

                notify({
                    'script_status': 'success',
                    'script_id': self.__script,
                })

                db_obj = Script.objects.get(id=self.__script)
                db_obj.is_running = False
                db_obj.error_code = ''
                db_obj.set_last_started()
                db_obj.save()

                self.lock.release()
                return
            elif self.__state == SchedulerStatus.ERROR:
                logger.info("Scheduler is already finished. (ERROR)")

                notify({
                    'script_status': 'error',
                    'error_code': self.__error_code,
                    'script_id': self.__script,
                })

                db_obj = Script.objects.get(script=self.__script)
                db_obj.is_running = False
                db_obj.error_code = self.__error_code
                db_obj.save()

                self.lock.release()
                return

            self.lock.release()
