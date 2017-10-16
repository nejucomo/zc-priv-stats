import time


class OperationTimer (object):
    def __init__(self):
        self._inittime = time.time()
        self._last = self._inittime

    def tick(self):
        last = self._last
        now = time.time()
        self._last = now
        return 'Op: {.2f} seconds; Runtime: {.2f} seconds'.format(
            now - last,
            now - self._inittime,
        )
