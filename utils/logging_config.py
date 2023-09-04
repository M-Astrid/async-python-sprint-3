import logging
import traceback


def setup_logger():
    file_log = logging.FileHandler("Log.log")
    console_out = logging.StreamHandler()

    logging.basicConfig(
        handlers=(file_log, console_out),
        format="[%(asctime)s | %(levelname)s]: %(message)s",
        datefmt="%m.%d.%Y %H:%M:%S",
        level=logging.INFO,
    )


async def log_exc(func):
    async def wrapper(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except Exception:
            logging.error(traceback.print_exc())
            raise

    return wrapper