"""
This module provides a scheudler.
"""

import threading
import asyncio
import logging

from server.utils import notify
from .safeloop import SafeLoop

LOGGER = logging.getLogger("fsim.scheduler")


class SchedulerStatus:
    """
    A state based automata which runs is used to start `ScriptModel`s.
    The automata has the folloing states:
        INIT: 0
            The scheduler starts all relevant slaves.
        WAITING_FOR_SLAVES: 1
            The scheduler waits for all slaves to connect to the master.
        NEXT_STEP: 2
            The scheduler fetches the next index/stage and executes the
            relevant programs.
        WAITING_FOR_PROGRAMS_FILESYSTEMS: 3
            The scheduler waits for all prevoiusly started programs to finish.
        SUCCESS: 4
            The scheduler is in the end state and was successful.
        ERROR: 5
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
        Thread-safe function.

        This functions allows the task execution from the outside of the
        `Scheudler`.

        Parameters
        ----------
            args: list
                This args will be forwarded to `SafeLoop.spawn`
            kwargs: list
                This args will be forwarded to `SafeLoop.spawn`
        """
        with self.lock:
            self.loop.spawn(*args, **kwargs)

    def is_running(self):
        """
        Thread-safe function.

        Checks if the underlying task (this `Scheudler`) is still running in
        the event loop.

        Returns
        -------
        bool:
            If the task is still running.
        """
        with self.lock:
            if self.__task is not None:
                done = self.__task.done()
                LOGGER.debug(
                    "Task in Scheduler event loop is %s.",
                    "done" if done else "pending",
                )
            else:
                done = True

        return not done

    def should_stop(self):
        """
        Thread-safe function.

        Checks if the `Scheudler` should stop. This can be set by
        `Scheudler.stop()`.

        Returns
        -------
        bool:
            If this `Scheduler` should stop.
        """
        with self.lock:
            stop = self.__stop
        return stop

    def stop(self):
        """
        Thread-safe function.

        Sets the stop flag and waits for the `Scheudler` to finish.
        """
        with self.lock:
            self.__stop = True

        self.notify()

        with self.lock:
            if self.loop is not None:
                self.loop.close()
                self.loop = None

    def start(self, script):
        """
        Thread-safe function.

        Creates a new `SafeLoop` and run self into this loop.


        Parameters
        ----------
            script: int
                An identifier which can identifier the `ScriptModel`
                in the database.

        Returns
        -------
        bool:
            If the scheudler is not running.
        """
        if self.is_running():
            return False
        else:
            from .models import Script
            with self.lock:
                LOGGER.debug(
                    "Starting Scheudler in the event loop `%s`",
                    self.loop.ident,
                )

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

            return True

    def notify(self):
        """
        Thread-safe function.

        This function is called by someone who modified the data which are
        related to the `Scheudler`. If `notify` is called then this indicates
        that the related data has changed and the `Scheudler` could make a
        step.
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
        Fetches the next index/stage for the `Scheduler` and stores the value
        into `Scheudler.__index`.

        Returns
        -------
        old_index: int
            The previous index/stage.
        all_done: bool
            If no more indexes/stages are avialable.

        """
        from .models import (
            ScriptGraphPrograms,
            ScriptGraphFiles,
        )

        old_index = self.__index

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

        if query:
            self.__index = min(query)
            LOGGER.debug("Scheduler found next index %s", self.__index)
            all_done = False
        else:
            LOGGER.debug("Scheduler did not found any more indexes.")
            self.__index = -1
            all_done = True

        return (old_index, all_done)

    def slave_timeout_callback(self):
        """
        This function is called after an amount of time. If the internal state
        is still on `WAITING_FOR_SLAVES` then the `Scheudler` aborts.
        """

        if self.__state == SchedulerStatus.WAITING_FOR_SLAVES:
            LOGGER.error("Not all salves connected within the time limit.")
            self.__error_code = 'Not all slaves connected within 5 minutes.'
            self.__state = SchedulerStatus.ERROR
            self.__event.set()

    @asyncio.coroutine
    def __run__(self):
        """
        This functions maps every internal state to a seperated function.
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
        This functions handle the `INIT` state. And sending every relevant
        slave the Wake-On-Lan package.
        """
        from .models import Script, Slave
        from .controller import slave_wake_on_lan

        for slave_id in Script.get_involved_slaves(self.__script):
            slave = Slave.objects.get(id=slave_id)
            LOGGER.debug("Send WOL to the slave `%s`.", slave.name)
            slave_wake_on_lan(slave)

        self.__state = SchedulerStatus.WAITING_FOR_SLAVES
        self.__event.set()

        self.loop.spawn(300, self.slave_timeout_callback)

        notify({
            'script_status': 'waiting_for_slaves',
            'script_id': self.__script,
        })

    def __state_wait_slaves(self):
        """
        This funcitons handels the `WAITING_FOR_SLAVES` state. If not all
        slaves are connected yet this functions wait for them by waiting for
        the `Scheduler.notify` call.
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
        This function handles the `NEXT_STEP` state, where all programs are
        started and all filesystems are moved. If a program is started then it
        will be not started again. If a filesystem is moved already then it
        will be not moved agian.
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
                    if sgp.program.start_time > max_start_time:
                        max_start_time = sgp.program.start_time

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
        This functions handle the `WAITING_FOR_PROGRAMS_FILESYSTEMS` state
        where it checks the database for the program and filesystem status. If
        not all programs and filesystems are ready it will wait for the
        `Scheudler.notify` call to proceed.
        """
        from .models import (
            ScriptGraphPrograms,
            ScriptGraphFiles,
        )

        LOGGER.debug(
            "Waiting for programs and filesystems in stage `%s`.",
            self.__index,
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
                    filesystem.name,
                )
                return

        self.__state = SchedulerStatus.NEXT_STEP
        self.__event.set()

    def __state_success(self):
        """
        This function handles the `SUCCESS` state, where the `Scheudler`
        finishes without an error.
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
        This function handles the `ERROR` state, where the `Scheudler`
        finishes an error.
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
