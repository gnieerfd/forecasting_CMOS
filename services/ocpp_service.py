"""
services/ocpp_service.py
OCPP 1.6 Central System (server) stub for CMOS.
Requires: ocpp (from GitHub master), websockets>=11

Run as standalone:
    python services/ocpp_service.py

The server listens on ws://0.0.0.0:9000 and accepts ChargePoint connections.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    import websockets
    from ocpp.routing import on
    from ocpp.v16 import ChargePoint as _CPBase
    from ocpp.v16 import call_result
    from ocpp.v16.enums import Action, RegistrationStatus
    _OCPP_AVAILABLE = True
except ImportError:
    _OCPP_AVAILABLE = False
    logger.warning("ocpp / websockets library not available.")


if _OCPP_AVAILABLE:

    class ChargePoint(_CPBase):
        """Minimal OCPP 1.6 ChargePoint handler."""

        @on(Action.BootNotification)
        async def on_boot_notification(self, charge_point_vendor, charge_point_model, **kwargs):
            logger.info(f"BootNotification from {charge_point_vendor} / {charge_point_model}")
            return call_result.BootNotification(
                current_time=datetime.now(timezone.utc).isoformat(),
                interval=10,
                status=RegistrationStatus.accepted,
            )

        @on(Action.Heartbeat)
        async def on_heartbeat(self, **kwargs):
            return call_result.Heartbeat(
                current_time=datetime.now(timezone.utc).isoformat()
            )

        @on(Action.StartTransaction)
        async def on_start_transaction(self, connector_id, id_tag, meter_start, timestamp, **kwargs):
            logger.info(f"StartTransaction | connector={connector_id} tag={id_tag} meter={meter_start}")
            return call_result.StartTransaction(
                transaction_id=int(datetime.now().timestamp()),
                id_tag_info={"status": "Accepted"},
            )

        @on(Action.StopTransaction)
        async def on_stop_transaction(self, meter_stop, timestamp, transaction_id, **kwargs):
            logger.info(f"StopTransaction | id={transaction_id} meter_stop={meter_stop}")
            return call_result.StopTransaction(id_tag_info={"status": "Accepted"})

        @on(Action.MeterValues)
        async def on_meter_values(self, connector_id, meter_value, **kwargs):
            for mv in meter_value:
                for sv in mv.get("sampled_value", []):
                    logger.debug(
                        f"MeterValue | connector={connector_id} "
                        f"{sv.get('measurand','?')} = {sv.get('value','?')} {sv.get('unit','')}"
                    )
            return call_result.MeterValues()

        @on(Action.StatusNotification)
        async def on_status_notification(self, connector_id, error_code, status, **kwargs):
            logger.info(f"StatusNotification | connector={connector_id} status={status}")
            return call_result.StatusNotification()

    # ── Server ─────────────────────────────────────────────────────────────

    async def _on_connect(websocket, path):
        """Handle incoming WebSocket from a ChargePoint."""
        charge_point_id = path.strip("/")
        cp = ChargePoint(charge_point_id, websocket)
        logger.info(f"ChargePoint connected: {charge_point_id}")
        await cp.start()

    async def run_server(host: str = "0.0.0.0", port: int = 9000) -> None:
        server = await websockets.serve(
            _on_connect,
            host,
            port,
            subprotocols=["ocpp1.6"],
        )
        logger.info(f"OCPP 1.6 Central System listening on ws://{host}:{port}")
        await server.wait_closed()


def start_ocpp_server(host: str = "0.0.0.0", port: int = 9000) -> None:
    """Blocking call – run in a dedicated thread or process."""
    if not _OCPP_AVAILABLE:
        logger.error("Cannot start OCPP server: dependencies missing.")
        return
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server(host, port))


if __name__ == "__main__":
    start_ocpp_server()
