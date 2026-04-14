"""
services/mqtt_service.py
Lightweight MQTT client wrapper using paho-mqtt.
Used for subscribing to real-time energy readings from CS hardware.

Usage (in a background thread or separate process):
    client = CMOSMqttClient(broker="localhost", port=1883)
    client.connect()
    client.subscribe("cs/serpong/energy/#")
    client.loop_start()   # non-blocking
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


try:
    import paho.mqtt.client as mqtt
    _PAHO_AVAILABLE = True
except ImportError:
    _PAHO_AVAILABLE = False
    logger.warning("paho-mqtt not installed – MQTT service disabled.")


class CMOSMqttClient:
    """
    Thin wrapper around paho-mqtt for CMOS energy monitoring.

    Parameters
    ----------
    broker : str        MQTT broker hostname / IP
    port   : int        MQTT broker port (default 1883)
    client_id : str     MQTT client identifier
    on_message_cb : Callable  optional callback(topic, payload_dict)
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        client_id: str = "cmos_monitor",
        on_message_cb: Optional[Callable] = None,
    ) -> None:
        self.broker        = broker
        self.port          = port
        self.client_id     = client_id
        self._cb           = on_message_cb
        self._client       = None
        self._connected    = False
        self._latest: dict = {}

    # ── Connection ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        if not _PAHO_AVAILABLE:
            logger.error("paho-mqtt library missing.")
            return False
        try:
            self._client = mqtt.Client(client_id=self.client_id, clean_session=True)
            self._client.on_connect    = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message    = self._on_message
            self._client.connect(self.broker, self.port, keepalive=60)
            self._connected = True
            logger.info(f"MQTT connecting to {self.broker}:{self.port}")
            return True
        except Exception as exc:
            logger.error(f"MQTT connect failed: {exc}")
            return False

    def subscribe(self, topic: str, qos: int = 1) -> None:
        if self._client and self._connected:
            self._client.subscribe(topic, qos=qos)
            logger.info(f"MQTT subscribed: {topic}")

    def loop_start(self) -> None:
        """Start non-blocking network loop."""
        if self._client:
            self._client.loop_start()

    def loop_stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    # ── Callbacks ─────────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("MQTT connected.")
        else:
            logger.error(f"MQTT connection refused (rc={rc}).")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning(f"MQTT disconnected (rc={rc}).")

    def _on_message(self, client, userdata, msg):
        topic   = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw": msg.payload.decode("utf-8", errors="replace")}

        # Update in-memory latest reading
        self._latest = {
            "topic":     topic,
            "payload":   payload,
            "received":  datetime.utcnow().isoformat(),
        }
        logger.debug(f"MQTT msg | {topic}: {payload}")

        if self._cb:
            try:
                self._cb(topic, payload)
            except Exception as exc:
                logger.error(f"MQTT callback error: {exc}")

    # ── Getters ───────────────────────────────────────────────────────────

    @property
    def latest(self) -> dict:
        """Return the most recent message received."""
        return self._latest

    @property
    def is_connected(self) -> bool:
        return self._connected

    def publish(self, topic: str, payload: dict | str, qos: int = 1) -> None:
        if not self._client or not self._connected:
            logger.warning("MQTT not connected – cannot publish.")
            return
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        self._client.publish(topic, payload, qos=qos)
