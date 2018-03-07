"""
This module provides an event loop with basic functions.
"""

import asyncio
import threading
import logging
import uuid

LOGGER = logging.getLogger("fsim.event_loop")


class SafeLoop:
    """
    Wraps an event loop in another thread.
    """

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = None
        self.ident = uuid.uuid4().hex

    def spawn(self, time, function, *args):
        """
        Wraps the `function` into a task and adds it to the event loop. The
        function will be executed after the specified amount of `time` is
        elapsed.

        Parameters
        ----------
            time: number
                Waits the specified amount of `time` before execution.
            function: function
                This `function` will be executed into the event loop.
            args: list
                This will be forwarded to the given `function`.

        """
        LOGGER.debug(
            "Spawning function after %s into the event loop `%s` (in thread %s)",
            time,
            self.ident,
            self.thread.ident,
        )
        self.loop.call_soon_threadsafe(self.loop.call_later, time, function,
                                       *args)

    def run(self, function, *args):
        """
        Runs a future in the event loop without any timeout.

        Parameter
        ---------
            function: function
                This `function` will be executed into the event loop.
            args: list
                This will be forwarded to the given `function`.
        """
        LOGGER.debug(
            "Spawning function into the event loop `%s` (in thread %s)",
            self.ident,
            self.thread.ident,
        )
        self.loop.call_soon_threadsafe(function, *args)

    def create_task(self, coro):
        """
        Wrapper function for the `AbstractEventLoop.create_task` which returns
        the task handle.

        Parameters
        ----------
            coro: function (with @async.coroutine)
                A task which will be spawned into the event loop.

        Returns
        -------
            A task handle for the spawned task.
        """
        task = self.loop.create_task(coro)
        return task

    def __run__(self):
        LOGGER.debug("Running event loop `%s` in thread %s.", self.ident,
                     self.thread.ident)
        self.loop.run_forever()
        LOGGER.debug("The event loop `%s` has finished.", self.ident)

    def start(self):
        """
        Initilizes the whole event loop with a seperated thread, where the
        event loop is running.
        """

        if self.thread is None:
            self.thread = threading.Thread(
                target=self.__run__,
                daemon=True,
            )

            self.thread.start()
            LOGGER.debug(
                "Starting thread `%s` for event loop `%s`.",
                self.ident,
                self.thread.ident,
            )
