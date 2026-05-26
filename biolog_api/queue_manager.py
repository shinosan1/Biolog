from queue import Queue

_write_queue: Queue = Queue(maxsize=100)


def get_queue() -> Queue:
    return _write_queue
