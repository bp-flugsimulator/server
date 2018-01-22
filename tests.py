import threading
import asyncio
import random
import time


loop = asyncio.get_event_loop()

@asyncio.coroutine
def sleep_and_print():
    time = random.randrange(0, 10, 1)
    yield from asyncio.sleep(time)
    print("I was sleeping for " + str(time))


def x():
    for x in range(0, 10):
        loop.create_task(sleep_and_print())
for y in range(0,10):
    threading.Thread(target=x).start()

loop.run_forever()

