"""
This module contains a scheduler which runs programs on the different clients.
"""

import threading
import asyncio
import logging

from server.utils import notify
from .safeloop import SafeLoop

LOGGER = logging.getLogger("fsim.scheduler")


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

    WAITING_FOR_PROGRAMS_FILESYSTEMS
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
    WAITING_FOR_PROGRAMS_FILESYSTEMS = 3
    SUCCESS = 4
    ERROR = 5


class Scheduler:
    """
    A thread-safe scheduler which starts programs from a slave.
    """

    def __init__(self):
        self.lock = threading.Lock()

        self.loop = SafeLoop()
        self.loop.start()

        self.__event = None
        self.__task = None
        self.__error_code = None
        self.__stop = False
        self.__state = SchedulerStatus.INIT
        self.__index = None
        self.__script = None

    def spawn(self, *args, **kwargs):
        """
        Forwards to self.
        """
        self.lock.acquire()
        self.loop.spawn(*args, **kwargs)
        self.lock.release()

    def is_running(self):
        """
        This function is thread-safe.

        Returns true if the underlying thread is still running.

        Returns
        -------
            bool
        """
        self.lock.acquire()

        if self.__task is not None:
            done = self.__task.done()
            LOGGER.debug(
                "Task in Scheduler event loop is %s.",
                "done" if done else "pending",
            )
        else:
            done = True

        self.lock.release()
        return not done

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
        self.lock.release()

        self.notify()

        self.lock.acquire()

        if self.__task is not None:
            self.__task.cancel()
            self.__task = None

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
            LOGGER.debug("Adding task to scheduler event loop")

            self.__error_code = None
            self.__stop = False
            self.__state = SchedulerStatus.INIT
            self.__index = None
            self.__script = script
            self.__event = asyncio.Event(loop=self.loop.loop)

            self.__task = self.loop.create_task(self.__run__())

            Script.objects.filter(id=self.__script).update(
                is_running=True,
                is_initialized=True,
                current_index=-1,
            )

            self.lock.release()
            return True

    def notify(self):
        """
        This function is thread-safe.

        Notifies the scheduler that something has changed. That means the
        scheduler will look at the data again.
        """
        if self.is_running():
            LOGGER.debug("Send notify to task in scheduler event loop.")

            def callback():
                """
                Run the __event.set in the Event Loop and not outside!
                """
                if not self.__event.is_set():
                    self.__event.set()

            self.loop.run(callback)

    def __get_next_stage(self):
        """
        Generates the next stage and returns the number of the last stage and
        if this stage is valid.

        Returns
        --------
            last index and if this stage is valid

        """
        from .models import (
            ScriptGraphPrograms,
            ScriptGraphFiles,
        )

        old_index = self.__index

        try:
            query_programs = ScriptGraphPrograms.objects.filter(
                script=self.__script,
                index__gt=self.__index,
            ).values_list(
                'index',
                flat=True,
            )

            query_filesystems = ScriptGraphFiles.objects.filter(
                script=self.__script,
                index__gt=self.__index,
            ).values_list(
                'index',
                flat=True,
            )

            query = set(query_filesystems).union(set(query_programs))

            self.__index = min(query)
            LOGGER.debug("Scheduler found next index %s", self.__index)
            all_done = False
        except IndexError:
            LOGGER.debug("Scheduler done")
            self.__index = -1
            all_done = True

        return (old_index, all_done)

    def timer_scheduler_slave_timeout(self):
        """
        Spawns a timer function into the event loop which will set the timeoute
        the scheduler if there was no progress.

        Arguments
        ---------
            scheduler: SchedulerStatus object
            time: Amount of time to wait
        """

        LOGGER.debug("Slave timeout call back.")
        if self.__state == SchedulerStatus.WAITING_FOR_SLAVES:
            LOGGER.debug("Scheduler for slaves timeouted")
            self.__error_code = 'Not all slaves connected within 5 minutes.'
            self.__state = SchedulerStatus.ERROR
            self.__event.set()

    @asyncio.coroutine
    def __run__(self):
        """
        Function wich will be executed by the Thread.
        """

        while True:
            LOGGER.debug("Scheduler is waiting for wakeup notification.")
            yield from self.__event.wait()
            self.__event.clear()
            LOGGER.debug("Scheduler is doing a step.")

            if self.__stop:
                LOGGER.info(
                    "Scheduler received interupt event. Exiting scheduler loop."
                )
                return

            if self.__state == SchedulerStatus.INIT:
                LOGGER.debug("State: INIT")
                self.__state_init()
            elif self.__state == SchedulerStatus.WAITING_FOR_SLAVES:
                LOGGER.debug("State: WAITING_FOR_SLAVES")
                self.__state_wait_slaves()
            elif self.__state == SchedulerStatus.NEXT_STEP:
                LOGGER.debug("State: NEXT_STEP")
                self.__state_next()
            elif self.__state == SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS:
                LOGGER.debug("State: WAITING_FOR_PROGRAMS_FILESYSTEMS")
                self.__state_wait_programs_filesystems()
            elif self.__state == SchedulerStatus.SUCCESS:
                LOGGER.debug("State: SUCCESS")
                self.__state_success()
                LOGGER.debug("Scheduler has finished ... exiting.")
                return
            elif self.__state == SchedulerStatus.ERROR:
                LOGGER.debug("State: ERROR")
                self.__state_error()
                LOGGER.debug("Scheduler has finished ... exiting.")
                return

    def __state_init(self):
        """
        In this state all slaves are started.
        """
        from .models import Script, Slave
        from .controller import slave_wake_on_lan

        for slave_id in Script.get_involved_slaves(self.__script):
            slave = Slave.objects.get(id=slave_id)
            LOGGER.debug("Send WOL to the slave `%s`.", slave.name)
            slave_wake_on_lan(slave)

        self.__state = SchedulerStatus.WAITING_FOR_SLAVES
        self.__event.set()

        self.loop.spawn(300, self.timer_scheduler_slave_timeout)

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
            LOGGER.info("All slaves are online ... continue with execution.")
            self.__state = SchedulerStatus.NEXT_STEP
            self.__index = -1
            self.__event.set()
        else:
            LOGGER.info("Waiting for all slaves to be online.")

    def __state_next(self):
        """
        In this state the next index is selected and the programs are started.
        """
        from .controller import prog_start, fs_move
        from .errors import (
            FilesystemMovedError,
            ProgramRunningError,
            SlaveOfflineError,
        )
        from .models import (
            Script,
            ScriptGraphPrograms,
            ScriptGraphFiles,
        )

        (last_index, all_done) = self.__get_next_stage()
        max_start_time = 0

        LOGGER.info(
            "Starting programs and moving files for stage `%s`",
            self.__index,
        )

        Script.objects.filter(id=self.__script).update(
            current_index=self.__index)

        if all_done:
            LOGGER.info(
                "Could not find another index after `%s` ... done.",
                last_index,
            )
            self.__state = SchedulerStatus.SUCCESS
            self.__event.set()
        else:
            notify_me = False
            for sgp in ScriptGraphPrograms.objects.filter(
                    script=self.__script,
                    index=self.__index,
            ):
                try:
                    prog_start(sgp.program)
                    LOGGER.info("Started program `%s`", sgp.program.name)
                except ProgramRunningError as err:
                    LOGGER.info("Program `%s` is already started.", err.name)
                    notify_me = True
                    continue
                except SlaveOfflineError as err:
                    LOGGER.error(
                        "A slave is gone offline while the execution.")
                    self.__state = SchedulerStatus.ERROR
                    self.__error_code = str(err)
                    self.__event.set()
                    return

            for sgf in ScriptGraphFiles.objects.filter(
                    script=self.__script,
                    index=self.__index,
            ):
                try:
                    fs_move(sgf.filesystem)
                    LOGGER.info("Moved filesystem `%s`", sgf.filesystem.name)
                except FilesystemMovedError as err:
                    # if the filesystem is already moved go on.
                    LOGGER.info("Filesystem `%s` is already moved.", err.name)
                    notify_me = True
                except SlaveOfflineError as err:
                    LOGGER.error(
                        "A slave is gone offline while the execution.")
                    self.__state = SchedulerStatus.ERROR
                    self.__error_code = str(err)
                    self.__event.set()
                    return

            LOGGER.info(
                "Started all programs for stage `%s`.",
                self.__index,
            )

            self.__state = SchedulerStatus.WAITING_FOR_PROGRAMS_FILESYSTEMS
            if notify_me:
                LOGGER.info(
                    "Notify myself because some entries are already ready.")
                self.__event.set()

        notify({
            'script_status': 'next_step',
            'index': self.__index,
            'last_index': last_index,
            'start_time': max_start_time,
            'script_id': self.__script,
        })

    def __state_wait_programs_filesystems(self):
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

        filesystems = ScriptGraphFiles.objects.filter(
            script=self.__script,
            index=self.__index,
        )

        for sgp in progs:
            prog = sgp.program

            if prog.is_error:
                LOGGER.debug("Error in program: %s", prog.name)
                self.__state = SchedulerStatus.ERROR
                self.__error_code = "Program {} has an error.".format(
                    prog.name)
                self.__event.set()
                return

            elif prog.is_running and not prog.is_timeouted:
                LOGGER.debug(
                    "Program %s is not ready yet.",
                    prog.name,
                )
                return

        for sgf in filesystems:
            filesystem = sgf.filesystem

            if filesystem.is_error:
                LOGGER.debug("Error in filesystem: %s", filesystem.name)
                self.__state = SchedulerStatus.ERROR
                self.__error_code = "Filesystem {} has an error.".format(
                    filesystem.name)
                self.__event.set()
                return

            elif not filesystem.is_moved:
                LOGGER.debug(
                    "Filesystem %s is not ready yet.",
                    prog.name,
                )
                return

        self.__state = SchedulerStatus.NEXT_STEP
        self.__event.set()

    def __state_success(self):
        """
        In this state the scheduler clean up and save the results.
        """
        from .models import Script

        LOGGER.info("Scheduler is finished. (SUCCESS)")

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

        LOGGER.info("Scheduler is finished. (ERROR)")

        Script.objects.filter(id=self.__script).update(
            is_running=False,
            error_code=self.__error_code,
        )

        notify({
            'script_status': 'error',
            'error_code': self.__error_code,
            'script_id': self.__script,
        })
