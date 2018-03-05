"""
Safe loop
"""

import asyncio
import threading
import logging

LOGGER = logging.getLogger("fsim.event_loop")


class SafeLoop:
    """
    Event loop with locks for multi threading.
    """

    def __init__(self):
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
        LOGGER.debug("Spawned task in event loop in thread %s", self.thread)
        self.loop.call_soon_threadsafe(self.loop.call_later, timer, function,
                                       *args)

    def run(self, function, *args):
        """
        Thread-safe function.

        Runs a future in the event loop without any timeout.

        Arguments
        ---------
            function: callable function

        """
        LOGGER.debug(
            "Spawn function callback into event loop without timeout.")
        self.loop.call_soon_threadsafe(function, *args)

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
        LOGGER.debug("Spawn task into event loop.")
        task = self.loop.create_task(coro)
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
