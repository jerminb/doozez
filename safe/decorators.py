import functools

from .models import DoozezTaskType

__tasks = {}


def doozez_task(_func=None, *, type: DoozezTaskType):
    def decorator_doozez_task(func):
        __tasks[type.value] = func

    if _func is None:
        return decorator_doozez_task
    else:
        return decorator_doozez_task(_func)


def run(type: str, *args, **kargs):
    return __tasks[type](*args, **kargs)


def clear():
    __tasks = {}
