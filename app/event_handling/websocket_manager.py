import asyncio
from typing import Dict
from uuid import uuid4

from fastapi import WebSocket
from fastapi_websocket_pubsub import PubSubClient

from shared import WEBHOOKS_URL
from shared.log_config import get_logger

logger = get_logger(__name__)


class WebsocketManager:
    """
    A class for managing websocket connections and establishing PubSub callbacks
    """

    _clients: Dict[str, PubSubClient] = {}

    @staticmethod
    async def subscribe(
        websocket: WebSocket, wallet_id: str = "", topic: str = ""
    ) -> str:
        """
        Subscribe a websocket connection to a specific topic.
        Returns a string representing a unique ID for this client
        """
        if not WebsocketManager._client:
            await WebsocketManager.start_pubsub_client()

        async def callback(data: str, topic: str):
            """
            Callback function for handling received webhook events.
            Note: PubSubClient expects a topic argument in callback
            """
            await websocket.send_text(data)

        if wallet_id and topic:
            subscribed_topic = f"{topic}-{wallet_id}"
        elif wallet_id:
            subscribed_topic = wallet_id
        elif topic:
            subscribed_topic = topic
        else:
            logger.error("Subscribe requires `topic` or `wallet_id` in request.")
            return

        client = PubSubClient()
        client.subscribe(subscribed_topic, callback)
        await WebsocketManager.start_pubsub_client(client)

        uuid = uuid4().hex
        WebsocketManager._clients[uuid] = client

        return uuid

    @staticmethod
    async def start_pubsub_client(client: PubSubClient, timeout: float = 10):
        """
        Start listening for webhook events on the Webhooks pubsub endpoint with a specified timeout.
        """

        async def ensure_connection_ready():
            """
            Ensure the connection is established before proceeding
            """
            websocket_url = convert_url_to_websocket(WEBHOOKS_URL)
            client.start_client(websocket_url + "/pubsub")
            await client.wait_until_ready()

        try:
            logger.debug("Starting PubSubClient for new websocket connection")
            await asyncio.wait_for(ensure_connection_ready(), timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning("Starting a PubSubClient has timed out after {}s.", timeout)
            await WebsocketManager.disconnect(client)
            raise WebsocketTimeout("Starting PubSubClient has timed out.") from e

    @staticmethod
    async def shutdown(client: PubSubClient, timeout: float = 3):
        """
        Shutdown the Websocket client and clear the connections with a specified timeout.
        """
        logger.debug("Shutting down Websocket client")

        async def wait_for_shutdown():
            await client.disconnect()

        try:
            await asyncio.wait_for(wait_for_shutdown(), timeout=timeout)
        except asyncio.TimeoutError as e:
            logger.warning(
                "Shutting down a PubSubClient has timed out after {}s.", timeout
            )
            raise WebsocketTimeout("PubSubClient shutdown has timed out.") from e

    @staticmethod
    async def disconnect_all():
        """
        Disconnect all Websocket clients and clear the connections.
        """
        if WebsocketManager._clients:
            logger.debug(
                "Disconnecting {} Websocket clients", len(WebsocketManager._clients)
            )
            for client in WebsocketManager._clients.values():
                try:
                    await WebsocketManager.disconnect(client)
                except WebsocketTimeout:
                    continue

            WebsocketManager._clients.clear()


class WebsocketTimeout(Exception):
    """Exception raised when Websocket functions time out."""


def convert_url_to_websocket(url: str) -> str:
    """
    Convert an HTTP or HTTPS URL to WebSocket (WS or WSS) URL.
    """
    if url.startswith("http"):
        return "ws" + url[4:]
    else:
        return url
