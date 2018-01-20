from threading import Timer
import threading

import logging
from .utils import notify, notify_err

logger = logging.getLogger("scheduler")


def timer_scheduler_slave_timeout(scheduler):
    """

    Arguments
    ---------
        scheduler: SchedulerStatus object
    """
    logger.debug("Scheduler timeouted")
    scheduler.set_error("Waiting for slaves timedout.")
    scheduler.stop()


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

    def set_error(self, error_code):
        """
        This function is thread-safe.

        Sets the error message for the scheduler.

        Arguments
        ---------
            error_code: object
        """
        self.lock.acquire()
        self.__error_code = error_code
        self.lock.release()

    def get_error(self):
        """
        This function is thread-safe.

        Returns the previous set error code. The
        code can set by a user or the scheduler.

        Returns
        ---------
            object
        """
        self.lock.acquire()
        error = self.__error_code
        self.lock.release()
        return error

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
        self.lock.acquire()

        if self.__thread != None:
            self.lock.release()
            return False
        else:
            self.__error_code = None
            self.__stop = False
            self.__thread = threading.Thread(
                daemon=True,
                target=self.__run__,
                args=(
                    SchedulerStatus.INIT,
                    script,
                    -1,
                ))
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

    def __run__(self, state, script, index):
        """
        Function wich will be executed by the Thread.

        Arguments
        ---------
            self: Scheduler
            state: Initiale state
            script: stript identifier
            index: Initiale index
        """
        from .models import (
            Slave,
            Script,
            ScriptGraphPrograms,
            ScriptGraphFiles,
            Program,
            File,
        )

        def get_next_index(index):
            try:
                query = ScriptGraphPrograms.objects.filter(
                    script=script,
                    index__gt=index,
                ).order_by('index')

                index = query[0].index
                logger.debug("Scheduler found next index " + str(index))
                all_done = False
            except IndexError:
                logger.debug("Scheduler done")
                index = -1
                all_done = True

            return (index, all_done)

        event = self.event
        last_index = index

        while event.wait():
            event.clear()

            if self.should_stop():
                break

            logger.debug("Lock Locked")
            self.lock.acquire()

            logger.debug("Current state: {}".format(state))
            if state == SchedulerStatus.INIT:
                for slave in Script.objects.get(
                        id=script).get_involved_slaves():
                    logger.debug("Starting slave `{}`".format(slave.name))
                    slave.wake_on_lan()

                Timer(
                    300.0,
                    timer_scheduler_slave_timeout,
                    (self, ),
                ).start()

                notify({
                    'script_status': 'waiting_for_slaves',
                })

                state = SchedulerStatus.WAITING_FOR_SLAVES
                event.set()
            elif state == SchedulerStatus.WAITING_FOR_SLAVES:
                if Script.objects.get(id=script).check_online():
                    logger.info("All slaves online")
                    (new_index, done) = get_next_index(index)
                    last_index = index
                    index = new_index
                    state = SchedulerStatus.NEXT_STEP
                    event.set()

                else:
                    logger.info("Waiting for all slaves to be online.")
            elif state == SchedulerStatus.NEXT_STEP:
                logger.info("Starting program for stage {}".format(index))

                max_start_time = 0

                for sgp in ScriptGraphPrograms.objects.filter(
                        script=script,
                        index=index,
                ):
                    if max_start_time < sgp.program.start_time:
                        max_start_time = sgp.program.start_time
                    sgp.program.enable()

                notify({
                    'script_status': 'next_step',
                    'index': index,
                    'last_index': last_index,
                    'start_time': max_start_time,
                })

                state = SchedulerStatus.WAITING_FOR_PROGRAMS
            elif state == SchedulerStatus.WAITING_FOR_PROGRAMS:
                logger.info("Waiting for programs to finish")

                progs = ScriptGraphPrograms.objects.filter(
                    script=script,
                    index=index,
                )

                step = True

                for sgp in progs:
                    prog = sgp.program
                    if prog.is_error:
                        logger.debug("Error in program {}".format(prog.name))
                        state = SchedulerStatus.ERROR
                        self.set_error("Program {} has an error.".format(
                            prog.name))
                        step = False
                        event.set()

                        break
                    elif prog.is_running and not prog.is_timeouted:
                        logger.debug("Program {} is not ready yet {}".format(
                            prog.name, vars(prog.programstatus)))
                        step = False

                        break
                if step:
                    logger.debug("Scheduler is doing the next step")
                    (new_index, all_done) = get_next_index(index)
                    last_index = index
                    index = new_index

                    if all_done:
                        logger.info("Everything done ... scheduler done")
                        state = SchedulerStatus.SUCCESS
                        event.set()

                    else:
                        logger.debug("Going into the next iteration")
                        state = SchedulerStatus.NEXT_STEP
                        event.set()
                else:
                    logger.info("Not all programs are finished")
            elif state == SchedulerStatus.SUCCESS:
                logger.info("Scheduler is already finished. (SUCCESS)")

                logger.debug("Lock Released")

                notify({
                    'script_status': 'success',
                })

                db_obj = Script.objects.get(id=script)
                db_obj.is_running = False
                db_obj.error_code = ''
                db_obj.set_last_started()
                db_obj.save()

                self.lock.release()
                break
            elif state == SchedulerStatus.ERROR:
                logger.info("Scheduler is already finished. (ERROR)")

                logger.debug("Lock Released")

                notify({
                    'script_status': 'error',
                    'message': self.__error_code,
                })

                db_obj = Script.objects.get(script=script)
                db_obj.is_running = False
                db_obj.error_code = self.__error_code
                db_obj.save()

                self.lock.release()
                break
            else:
                logger.debug("Nothing todo.")

            logger.debug("Lock Released")
            self.lock.release()


try:
    if CURRENT_SCHEDULER is None:
        CURRENT_SCHEDULER = Scheduler()
except NameError:
    CURRENT_SCHEDULER = Scheduler()
