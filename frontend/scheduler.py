from threading import Timer
import threading

import logging

logger = logging.getLogger("scheduler")


def timer_scheduler_slave_timeout(scheduler):
    """

    Arguments
    ---------
        scheduler: SchedulerStatus object
    """
    logger.debug("Slave online check timeouted for script " + str(me.name))
    scheduler.set_timeouted()
    scheduler.set_error("Waiting for slaves timedout.")


class SchedulerStatus:
    INIT = 0
    WAITING_FOR_SLAVES = 1
    NEXT_STEP = 2
    WAITING_FOR_PROGRAMS = 3
    SUCCESS = 4
    ERROR = 5


class Scheduler:
    def __init__(self):
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.__thread = None
        self.__timeouted = False
        self.__error_code = None

    def is_running(self):
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

    def set_timeouted(self):
        self.lock.acquire()
        self.__timeouted = True
        self.lock.release()

    def is_timeouted(self):
        self.lock.acquire()
        timeouted = self.__timeouted
        self.lock.release()
        return timeouted

    def set_error(self, error_code):
        self.lock.acquire()
        self.__error_code = error_code
        self.lock.release()

    def get_error(self):
        self.lock.acquire()
        error = self.__error_code
        self.lock.release()
        return error

    def start(self, script):
        self.lock.acquire()

        if self.__thread != None:
            self.lock.release()
            return False
        else:
            self.__thread = threading.Thread(
                target=self.__run__, args=(
                    SchedulerStatus.INIT,
                    script,
                    -1,
                ))
            self.__thread.start()
            self.lock.release()
            return True

    def notify(self):
        if self.is_running() and not self.event.is_set():
            self.event.set()

    def __run__(self, state, script, index):
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
                index = ScriptGraphPrograms.objects.filter(
                    index__gt=index).order_by('-index')[0].index
                logger.debug("Scheduler found next index " + str(index))
                all_done = False
            except IndexError:
                logger.debug("Scheduler done")
                index = -1
                all_done = True

            return (index, all_done)

        event = self.event

        logger.debug("Waiting for event")
        while event.wait():
            event.clear()

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

                state = SchedulerStatus.WAITING_FOR_SLAVES
                event.set()
            elif state == SchedulerStatus.WAITING_FOR_SLAVES:
                if self.is_timeouted():
                    logger.info("Timout reached for WAITING_FOR_SLAVES")
                    state = SchedulerStatus.ERROR
                    event.set()
                elif Script.objects.get(id=script).check_online():
                    logger.info("All slaves online")
                    (new_index, done) = get_next_index(index)
                    index = new_index
                    state = SchedulerStatus.NEXT_STEP

                    event.set()
                else:
                    logger.info("Waiting for all slaves to be online.")
            elif state == SchedulerStatus.NEXT_STEP:
                logger.info("Starting program for iteration {}".format(index))

                for sgp in ScriptGraphPrograms.objects.filter(
                        script=script,
                        index=index,
                ):
                    sgp.program.enable()

                state = SchedulerStatus.WAITING_FOR_PROGRAMS
            elif state == SchedulerStatus.WAITING_FOR_PROGRAMS:
                logger.info("Waiting for programs to finish")

                progs = ScriptGraphPrograms.objects.filter(
                    script=script,
                    index=index,
                )

                step = False if len(progs) == 0 else True

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
                    index = new_index

                    if all_done:
                        logger.info("Everything done ... scheduler done")
                        state = SchedulerStatus.SUCCESS
                        event.set()

                    else:
                        logger.info("Going into the next iteration")
                        state = SchedulerStatus.NEXT_STEP
                        event.set()
                else:
                    logger.info("Not all programs are finished")

            elif state == SchedulerStatus.SUCCESS:
                logger.debug("Scheduler is already finished. (SUCCESS)")
                #TODO: notify user bc of end
            elif state == SchedulerStatus.ERROR:
                logger.debug("Scheduler is already finished. (ERROR)")
                #TODO: notify user bc of end
            else:
                logger.debug("Nothing todo.")


try:
    if CURRENT_SCHEDULER is None:
        CURRENT_SCHEDULER = Scheduler()
except NameError:
    CURRENT_SCHEDULER = Scheduler()
