"""
This module contains the configuration of the 'frontend' application
"""
import builtins
import asyncio
import threading
import logging

from django.apps import AppConfig
from django.db.utils import OperationalError
from .scheduler import Scheduler

LOGGER = logging.getLogger("fsim.event_loop")


def flush(*tables):
    """
    Deletes all entries in the given tables.

    Arguments
    ---------
        tables: List of table names (as string)

    """
    from frontend import models

    for table in tables:
        try:
            getattr(models, table).objects.all().delete()
        except AttributeError:
            pass
        except OperationalError:
            pass


class SafeLoop:
    """
    Event loop with locks for multi threading.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.loop = asyncio.new_event_loop()
        self.thread = None

    def spawn(self, timer, function, *args):
        """
        Thread-safe function.

        Creates a task and adds it to the loop.

        Arguments
        ---------
            function: callable function

        """
        self.lock.acquire()
        LOGGER.debug("Spawned task in event loop in thread %s", self.thread)
        self.loop.call_soon_threadsafe(self.loop.call_later, timer, function,
                                       *args)
        self.lock.release()

    def run(self, function, *args):
        """
        Thread-safe function.

        Runs a future in the event loop without any timeout.

        Arguments
        ---------
            function: callable function

        """
        self.lock.acquire()
        LOGGER.debug(
            "Spawn function callback into event loop without timeout.")
        self.loop.call_soon_threadsafe(function, *args)
        self.lock.release()

    def create_task(self, coro):
        """
        Thread-safe function.

        Creates a task in the event loop.

        Arguments
        ---------
            coro: Coroutine

        Returns
        -------
            TaskHandle
        """
        self.lock.acquire()
        LOGGER.debug("Spawn task into event loop.")
        task = self.loop.create_task(coro)
        self.lock.release()
        return task

    def __run__(self):
        LOGGER.debug(
            "Running  event loop %s in thread %s.",
            self.loop,
            self.thread,
        )
        self.loop.run_forever()
        LOGGER.debug("Event loop finished.")

    def start(self):
        """
        Thread safe function.

        Starts the event loop in another thread.
        """
        self.lock.acquire()

        LOGGER.debug("Starting thread %s ", self.thread)

        if self.thread is None:
            self.thread = threading.Thread(
                target=self.__run__,
                daemon=True,
            )

            self.thread.start()

            LOGGER.debug(
                "Thread started %s and is started %s. %s",
                self.thread.ident,
                self.thread.is_alive(),
                self.thread,
            )

        self.lock.release()


class FrontendConfig(AppConfig):
    """
    configures the frontend applications
    """
    name = 'frontend'

    def ready(self):
        # add FSIM_CURRENT_SCHEDULER to the builtins which make it
        # avialabel in every module
        builtins.FSIM_CURRENT_SCHEDULER = Scheduler()

        # create a event loop which is available in every module.
        # this is used to spawn timed tasks.
        builtins.FSIM_CURRENT_EVENT_LOOP = SafeLoop()
        builtins.FSIM_CURRENT_EVENT_LOOP.start()

        LOGGER.debug("Thread is %s", builtins.FSIM_CURRENT_EVENT_LOOP.thread)

        try:
            from .models import Slave
            Slave.objects.all().update(online=False, command_uuid=None)
        except OperationalError:
            pass

        try:
            from .models import Script
            Script.objects.all().update(
                error_code="",
                is_running=False,
                is_initialized=False,
                current_index=-1,
            )
        except OperationalError:
            pass

        # Flush status tables DO NOT DELETE!
        flush('ProgramStatus')
