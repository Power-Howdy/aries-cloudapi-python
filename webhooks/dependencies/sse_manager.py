import asyncio
import logging
from collections import defaultdict as ddict
from contextlib import asynccontextmanager
from typing import Any, Generator, Tuple

from webhooks.dependencies.service import Service

LOGGER = logging.getLogger(__name__)


class SseManager:
    """
    Class to manage Server-Sent Events (SSE).
    """

    def __init__(self, service: Service, max_queue_size=20):
        self.service = service
        self.locks = ddict(asyncio.Lock)  # Concurrency management per wallet
        self.max = max_queue_size

        # The following nested defaultdict stores events per wallet_id, per topic
        # LifoQueue is used here so newest events are yielded first.
        self.events = ddict(lambda: ddict(lambda: asyncio.LifoQueue(maxsize=self.max)))
        # A copy is maintained so that events consumed from the above queue can be re-added.
        # This is so repeated requests can receive the same events. Regular Queue to preserve ordering.
        self.cache = ddict(lambda: ddict(lambda: asyncio.Queue(maxsize=self.max)))

    @asynccontextmanager
    async def sse_event_stream(
        self, wallet: str, topic: str
    ) -> Generator[asyncio.LifoQueue, Any, None]:
        """
        Create a SSE event stream for a topic using a provided service.

        Args:
            wallet: The ID of the wallet subscribing to the topic.
            topic: The topic for which to create the event stream.
        """
        async with self.locks[wallet]:
            queue = self.events[wallet][topic]

        try:
            yield queue
        finally:
            # refill the queue from the copy
            async with self.locks[wallet]:
                queue1, queue2 = await _copy_queue(self.cache[wallet][topic], self.max)
                self.events[wallet][topic] = queue1
                self.cache[wallet][topic] = queue2

    async def enqueue_sse_event(self, event: str, wallet: str, topic: str) -> None:
        """
        Enqueue a SSE event to be sent to a specific wallet for a specific topic.

        This function puts the event into the queue of the respective client.

        Args:
            event: The event to enqueue.
            wallet: The ID of the wallet to which to enqueue the event.
            topic: The topic to which to enqueue the event.
        """
        LOGGER.debug(
            "Enqueueing event for wallet '%s': %s",
            wallet,
            event,
        )

        async with self.locks[wallet]:
            # Check if queue is full and make room before adding events
            if self.events[wallet][topic].full():
                await self.events[wallet][topic].get()

            if self.cache[wallet][topic].full():
                await self.cache[wallet][topic].get()

            await self.events[wallet][topic].put(event)
            await self.cache[wallet][topic].put(event)


async def _copy_queue(
    queue: asyncio.Queue, maxsize: int
) -> Tuple[asyncio.LifoQueue, asyncio.Queue]:
    # Consuming a queue removes its content. Therefore, we create two new queues to copy one
    queue1, queue2 = asyncio.LifoQueue(maxsize), asyncio.Queue(maxsize)
    while not queue.empty():
        item = await queue.get()
        await queue1.put(item)
        await queue2.put(item)

    return queue1, queue2
