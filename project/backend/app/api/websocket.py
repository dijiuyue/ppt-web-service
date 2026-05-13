"""
PPT Master Web Service - WebSocket Routes.

Real-time pipeline status updates via WebSocket.
Supports connection management, broadcasting, and typed messages.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState

from app.core.schemas import (
    WSMessageType,
    ConfirmationNeededData,
    JobUpdateData,
    StepChangeData,
    StatusUpdateData,
    WebSocketMessage,
)

router = APIRouter()


# ────────────────────────────────
# Connection Manager
# ────────────────────────────────


class ConnectionManager:
    """Manages WebSocket connections for real-time project updates.

    Uses a project-based subscription model. Each WebSocket client
    subscribes to a specific project ID, and messages are broadcast
    only to clients subscribed to that project.
    """

    def __init__(self) -> None:
        # project_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> project_id
        self._client_projects: Dict[WebSocket, str] = {}
        # Connection metadata for diagnostics
        self._client_info: Dict[WebSocket, dict[str, Any]] = {}

    @property
    def active_connections(self) -> int:
        """Total number of active WebSocket connections."""
        return len(self._client_projects)

    @property
    def subscribed_projects(self) -> int:
        """Number of projects with active subscribers."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket, project_id: str) -> None:
        """Accept a new WebSocket connection for a project.

        Args:
            websocket: The WebSocket connection.
            project_id: Project UUID string the client is subscribing to.
        """
        await websocket.accept()

        # Track connection
        if project_id not in self._connections:
            self._connections[project_id] = set()
        self._connections[project_id].add(websocket)
        self._client_projects[websocket] = project_id
        self._client_info[websocket] = {
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
        }

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove.
        """
        project_id = self._client_projects.pop(websocket, None)
        self._client_info.pop(websocket, None)

        if project_id and project_id in self._connections:
            self._connections[project_id].discard(websocket)
            if not self._connections[project_id]:
                del self._connections[project_id]

    async def send_to_client(
        self, websocket: WebSocket, message: Dict[str, Any]
    ) -> None:
        """Send a message to a single client.

        Args:
            websocket: Target WebSocket.
            message: JSON-serializable message dict.
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except RuntimeError:
            # Connection already closed
            pass

    async def broadcast_to_project(
        self, project_id: str, message: Dict[str, Any]
    ) -> int:
        """Broadcast a message to all clients subscribed to a project.

        Args:
            project_id: Project UUID string.
            message: JSON-serializable message dict.

        Returns:
            Number of clients the message was sent to.
        """
        if project_id not in self._connections:
            return 0

        clients = list(self._connections[project_id])
        sent = 0
        for client in clients:
            try:
                if client.client_state == WebSocketState.CONNECTED:
                    await client.send_json(message)
                    sent += 1
            except RuntimeError:
                # Connection closed, clean up
                await self.disconnect(client)

        return sent

    async def send_status_update(
        self,
        project_id: str,
        project_status: str,
        current_step: str,
        step_status: str,
        message: Optional[str] = None,
    ) -> int:
        """Send a status_update message to project subscribers.

        Args:
            project_id: Project UUID.
            project_status: Current project status.
            current_step: Current pipeline step.
            step_status: Current step status.
            message: Optional human-readable message.

        Returns:
            Number of clients notified.
        """
        data = StatusUpdateData(
            project_status=project_status,  # type: ignore[arg-type]
            current_step=current_step,  # type: ignore[arg-type]
            step_status=step_status,  # type: ignore[arg-type]
            message=message,
        )
        return await self.broadcast_to_project(
            project_id,
            {
                "type": WSMessageType.STATUS_UPDATE.value,
                "data": data.model_dump(mode="json"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
            },
        )

    async def send_job_update(
        self,
        project_id: str,
        job_id: str,
        step: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> int:
        """Send a job_update message to project subscribers.

        Args:
            project_id: Project UUID.
            job_id: Pipeline job ID.
            step: Pipeline step.
            status: Job status.
            error_message: Optional error message.

        Returns:
            Number of clients notified.
        """
        data = JobUpdateData(
            job_id=job_id,
            step=step,  # type: ignore[arg-type]
            status=status,  # type: ignore[arg-type]
            error_message=error_message,
        )
        return await self.broadcast_to_project(
            project_id,
            {
                "type": WSMessageType.JOB_UPDATE.value,
                "data": data.model_dump(mode="json"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
            },
        )

    async def send_step_change(
        self,
        project_id: str,
        previous_step: str,
        current_step: str,
        step_status: str,
    ) -> int:
        """Send a step_change message to project subscribers.

        Args:
            project_id: Project UUID.
            previous_step: Previous pipeline step.
            current_step: New current step.
            step_status: New step status.

        Returns:
            Number of clients notified.
        """
        data = StepChangeData(
            previous_step=previous_step,  # type: ignore[arg-type]
            current_step=current_step,  # type: ignore[arg-type]
            step_status=step_status,  # type: ignore[arg-type]
        )
        return await self.broadcast_to_project(
            project_id,
            {
                "type": WSMessageType.STEP_CHANGE.value,
                "data": data.model_dump(mode="json"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
            },
        )

    async def send_error(
        self,
        project_id: str,
        error_message: str,
        error_code: Optional[str] = None,
    ) -> int:
        """Send an error message to project subscribers.

        Args:
            project_id: Project UUID.
            error_message: Human-readable error description.
            error_code: Optional error code.

        Returns:
            Number of clients notified.
        """
        return await self.broadcast_to_project(
            project_id,
            {
                "type": WSMessageType.ERROR.value,
                "data": {
                    "message": error_message,
                    "code": error_code,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
            },
        )

    async def send_confirmation_needed(
        self,
        project_id: str,
        confirmations: Optional[Dict[str, Any]] = None,
        confirmation_type: str = "eight_confirmations",
    ) -> int:
        """Send a confirmation_needed message to project subscribers.

        Args:
            project_id: Project UUID.
            confirmations: Current confirmation data for review.
            confirmation_type: Type of confirmation needed.

        Returns:
            Number of clients notified.
        """
        data = ConfirmationNeededData(
            confirmation_type=confirmation_type,
            confirmations=confirmations,
        )
        return await self.broadcast_to_project(
            project_id,
            {
                "type": WSMessageType.CONFIRMATION_NEEDED.value,
                "data": data.model_dump(mode="json"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
            },
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get connection manager statistics.

        Returns:
            Stats dict with connection counts.
        """
        return {
            "active_connections": self.active_connections,
            "subscribed_projects": self.subscribed_projects,
            "projects": {
                pid: len(clients)
                for pid, clients in self._connections.items()
            },
        }


# ──── Singleton Instance ────

ws_manager = ConnectionManager()


# ──── Routes ────


@router.websocket("/ws/projects/{project_id}")
async def project_websocket(
    websocket: WebSocket,
    project_id: str,
) -> None:
    """WebSocket endpoint for real-time project updates.

    Clients connect to /ws/projects/{project_id} to receive
    real-time updates about pipeline status, job progress, and errors.

    Message Format (client -> server):
        {"type": "ping"} - Keepalive ping
        {"type": "subscribe", "data": {}} - Subscribe confirmation

    Message Format (server -> client):
        {"type": "status_update", "data": {...}, "timestamp": "..."}
        {"type": "job_update", "data": {...}, "timestamp": "..."}
        {"type": "step_change", "data": {...}, "timestamp": "..."}
        {"type": "error", "data": {...}, "timestamp": "..."}
        {"type": "confirmation_needed", "data": {...}, "timestamp": "..."}
    """
    await ws_manager.connect(websocket, project_id)

    try:
        # Send initial connection confirmation
        await ws_manager.send_to_client(
            websocket,
            {
                "type": "connected",
                "data": {
                    "project_id": project_id,
                    "message": "WebSocket connected successfully",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client message with timeout for keepalive
                message = await asyncio.wait_for(
                    websocket.receive_json(), timeout=60.0
                )

                # Handle client messages
                msg_type = message.get("type", "")

                if msg_type == WSMessageType.PING.value:
                    await ws_manager.send_to_client(
                        websocket,
                        {
                            "type": WSMessageType.PONG.value,
                            "data": {},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                elif msg_type == "get_status":
                    # Client requesting current status - could query DB here
                    await ws_manager.send_to_client(
                        websocket,
                        {
                            "type": "status_response",
                            "data": {
                                "project_id": project_id,
                                "message": "Status request received",
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                else:
                    # Unknown message type
                    await ws_manager.send_to_client(
                        websocket,
                        {
                            "type": "error",
                            "data": {
                                "message": f"Unknown message type: {msg_type}",
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(
                            {
                                "type": WSMessageType.PING.value,
                                "data": {},
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                except RuntimeError:
                    break

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await ws_manager.disconnect(websocket)
