import asyncio
from logging import Logger
from typing import Callable, Tuple


async def coroutine_with_retry(
    coroutine_func: Callable, args: Tuple, logger: Logger, max_attempts=5, retry_delay=1
    result = None
    for attempt in range(max_attempts):
        try:
            result = await coroutine_func(*args)
            break
        except Exception as e:
            if attempt + 1 == max_attempts:
                logger.error("Maximum number of retries exceeded. Failing.")
                raise e  # Re-raise the exception if max attempts exceeded

            logger.warning(
                f"Failed to run coroutine (attempt {attempt + 1}). Retrying in {retry_delay} seconds..."
            )
            await asyncio.sleep(retry_delay)
    return result
