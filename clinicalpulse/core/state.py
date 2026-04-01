import time

start_time: float = 0.0


def set_start_time() -> None:
    global start_time
    start_time = time.time()


def get_uptime() -> float:
    return round(time.time() - start_time, 1)
