import threading


class ReaderWriterLock:
    def __init__(self):
        self._readers = 0
        self._read_lock = threading.Lock()
        self._write_lock = threading.Lock()

    # ------------------------
    # Acquire read lock
    # ------------------------
    def acquire_read(self):
        with self._read_lock:
            self._readers += 1

            # first reader blocks writers
            if self._readers == 1:
                self._write_lock.acquire()

    # ------------------------
    # Release read lock
    # ------------------------
    def release_read(self):
        with self._read_lock:
            self._readers -= 1

            # last reader releases writer lock
            if self._readers == 0:
                self._write_lock.release()

    # ------------------------
    # Acquire write lock
    # ------------------------
    def acquire_write(self):
        self._write_lock.acquire()

    # ------------------------
    # Release write lock
    # ------------------------
    def release_write(self):
        self._write_lock.release()