from random import choices
from time import time
from string import ascii_uppercase, digits
from logging import getLogger, config
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from os import path

config.fileConfig(
    path.join(path.dirname(path.abspath(__file__)), "../config/logging.conf"),
    disable_existing_loggers=False,
)

logger = getLogger(__name__)


class RequestLogger(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        idem = "".join(choices(ascii_uppercase + digits, k=6))
        logger.info(f"rid={idem} start request path={request.url.path}")
        start_time = time()
        response = await call_next(request)
        process_time = (time() - start_time) * 1000
        formatted_process_time = "{0:.2f}".format(process_time)
        logger.info(
            f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
        )

        return response
