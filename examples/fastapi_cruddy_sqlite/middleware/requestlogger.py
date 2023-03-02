import logging
import random
import time
import string
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from os import path

logging.config.fileConfig(
    path.join(path.dirname(path.abspath(__file__)), "../config/logging.conf"),
    disable_existing_loggers=False,
)

logger = logging.getLogger(__name__)


class RequestLogger(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        # some_attribute: str,
    ):
        super().__init__(app)
        # self.some_attribute = some_attribute

    async def dispatch(self, request: Request, call_next):
        idem = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        logger.info(f"rid={idem} start request path={request.url.path}")
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = "{0:.2f}".format(process_time)
        logger.info(
            f"rid={idem} completed_in={formatted_process_time}ms status_code={response.status_code}"
        )

        return response
