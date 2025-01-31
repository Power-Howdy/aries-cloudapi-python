import logging
import ssl
from typing import Optional

from fastapi import HTTPException
from httpx import AsyncClient, HTTPStatusError, Response

logger = logging.getLogger(__name__)

ssl_context = ssl.create_default_context()


# Async Client with built in error handling and re-using SSL certs
class RichAsyncClient(AsyncClient):
    def __init__(
        self,
        *args,
        name: Optional[str] = None,
        verify=ssl_context,
        raise_status_error=True,
        **kwargs,
    ) -> None:
        super().__init__(verify=verify, *args, **kwargs)
        self.name = (
            name + " - HTTP" if name else "HTTP"
        )  # prepend to exception messages to add context
        self.raise_status_error = raise_status_error

    async def post(self, url: str, **kwargs) -> Response:
        try:
            response = await super().post(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()  # Raise exception for 4xx and 5xx status codes
        except HTTPStatusError as e:
            code = e.response.status_code
            message = e.response.text
            log_message = f"{self.name} POST `{url}` failed. Status code: {code}. Response: `{message}`."
            logger.error(log_message)

            raise HTTPException(status_code=code, detail=message) from e
        return response

    async def get(self, url: str, **kwargs) -> Response:
        try:
            response = await super().get(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            message = e.response.text
            log_message = f"{self.name} GET `{url}` failed. Status code: {code}. Response: `{message}`."
            logger.error(log_message)

            raise HTTPException(status_code=code, detail=message) from e
        return response

    async def delete(self, url: str, **kwargs) -> Response:
        try:
            response = await super().delete(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            message = e.response.text
            log_message = f"{self.name} DELETE `{url}` failed. Status code: {code}. Response: `{message}`."
            logger.error(log_message)

            raise HTTPException(status_code=code, detail=message) from e
        return response

    async def put(self, url: str, **kwargs) -> Response:
        try:
            response = await super().put(url, **kwargs)
            if self.raise_status_error:
                response.raise_for_status()
        except HTTPStatusError as e:
            code = e.response.status_code
            message = e.response.text
            log_message = f"{self.name} PUT `{url}` failed. Status code: {code}. Response: `{message}`."
            logger.error(log_message)

            raise HTTPException(status_code=code, detail=message) from e
        return response
