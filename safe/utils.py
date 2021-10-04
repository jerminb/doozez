import random
import string
import traceback


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def exception_as_dict(ex, err):
    exc_type, exc_val, tb = err
    tb = ''.join(traceback.format_exception(
        exc_type,
        exc_val if isinstance(exc_val, exc_type) else exc_type(exc_val),
        tb
    ))
    return dict(type=ex.__class__.__name__,
                message=str(ex),
                traceback=tb)
