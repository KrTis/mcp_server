import time


class Stopwatch:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()
        self.end_time = None

    def stop(self):
        if self.start_time is None:
            raise ValueError("Stopwatch was never started")
        self.end_time = time.time()
        return self.end_time - self.start_time


stopwatches = {}
