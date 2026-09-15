"""
Supabase Service - Remote Database Operations

Handles all CRUD operations to Supabase for:
- Users
- Rooms
- Devices
- Telemetry logs
- Command logs
- Chat sessions and messages
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("supabase_service")


class SupabaseService:
    """Singleton service for Supabase database operations."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Supabase client."""
        if self._initialized:
            return

        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            logger.warning("supabase_not_configured", 
                         url_set=bool(settings.SUPABASE_URL),
                         key_set=bool(settings.SUPABASE_KEY))
            return

        try:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            self._initialized = True
            logger.info("supabase_initialized", url=settings.SUPABASE_URL)
        except Exception as e:
            logger.error("supabase_init_failed", error=str(e))
            raise

    @property
    def client(self) -> Client:
        """Get Supabase client (lazy init)."""
        if not self._initialized:
            self.initialize()
        if not self._client:
            raise RuntimeError("Supabase client not initialized")
        return self._client

    # ── Users ────────────────────────────────────────────────

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user in Supabase."""
        try:
            response = self.client.table("users").insert(user_data).execute()
            logger.info("user_created", user_id=user_data.get("id"))
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("user_create_failed", error=str(e), user_id=user_data.get("id"))
            raise

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from Supabase."""
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("user_get_failed", error=str(e), email=email)
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID from Supabase."""
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("user_get_failed", error=str(e), user_id=user_id)
            return None
            logger.error("user_get_failed", error=str(e), email=email)
            return None

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user in Supabase."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            response = self.client.table("users").update(updates).eq("id", user_id).execute()
            logger.info("user_updated", user_id=user_id)
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("user_update_failed", error=str(e), user_id=user_id)
            raise

    # ── Rooms ────────────────────────────────────────────────

    async def create_room(self, room_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create room in Supabase."""
        try:
            response = self.client.table("rooms").insert(room_data).execute()
            logger.info("room_created", room_id=room_data.get("id"), owner_id=room_data.get("owner_id"))
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("room_create_failed", error=str(e))
            raise

    async def get_rooms_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get all rooms for a user from Supabase."""
        try:
            response = self.client.table("rooms").select("*").eq("owner_id", owner_id).execute()
            return response.data or []
        except Exception as e:
            logger.error("rooms_get_failed", error=str(e), owner_id=owner_id)
            return []

    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update room in Supabase."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            response = self.client.table("rooms").update(updates).eq("id", room_id).execute()
            logger.info("room_updated", room_id=room_id)
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("room_update_failed", error=str(e), room_id=room_id)
            raise

    async def delete_room(self, room_id: str) -> bool:
        """Delete room from Supabase."""
        try:
            self.client.table("rooms").delete().eq("id", room_id).execute()
            logger.info("room_deleted", room_id=room_id)
            return True
        except Exception as e:
            logger.error("room_delete_failed", error=str(e), room_id=room_id)
            return False

    # ── Devices ──────────────────────────────────────────────

    async def create_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create device in Supabase."""
        try:
            response = self.client.table("devices").insert(device_data).execute()
            logger.info("device_created", device_id=device_data.get("id"), room_id=device_data.get("room_id"))
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("device_create_failed", error=str(e))
            raise

    async def get_devices_by_room(self, room_id: str) -> List[Dict[str, Any]]:
        """Get all devices in a room from Supabase."""
        try:
            response = self.client.table("devices").select("*").eq("room_id", room_id).execute()
            return response.data or []
        except Exception as e:
            logger.error("devices_get_failed", error=str(e), room_id=room_id)
            return []

    async def get_devices_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get all devices for a user from Supabase."""
        try:
            response = self.client.table("devices").select("*").eq("owner_id", owner_id).execute()
            return response.data or []
        except Exception as e:
            logger.error("devices_get_failed", error=str(e), owner_id=owner_id)
            return []

    async def update_device(self, device_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update device in Supabase."""
        try:
            updates["updated_at"] = datetime.utcnow().isoformat()
            response = self.client.table("devices").update(updates).eq("id", device_id).execute()
            logger.info("device_updated", device_id=device_id)
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("device_update_failed", error=str(e), device_id=device_id)
            raise

    async def delete_device(self, device_id: str) -> bool:
        """Delete device from Supabase."""
        try:
            self.client.table("devices").delete().eq("id", device_id).execute()
            logger.info("device_deleted", device_id=device_id)
            return True
        except Exception as e:
            logger.error("device_delete_failed", error=str(e), device_id=device_id)
            return False

    # ── Telemetry ────────────────────────────────────────────

    async def log_telemetry(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log telemetry to Supabase."""
        try:
            response = self.client.table("telemetry_logs").insert(telemetry_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("telemetry_log_failed", error=str(e), device_id=telemetry_data.get("device_id"))
            raise

    async def get_telemetry(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get telemetry logs for a device from Supabase."""
        try:
            response = (
                self.client.table("telemetry_logs")
                .select("*")
                .eq("device_id", device_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error("telemetry_get_failed", error=str(e), device_id=device_id)
            return []

    # ── Commands ─────────────────────────────────────────────

    async def log_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log command to Supabase."""
        try:
            response = self.client.table("command_logs").insert(command_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("command_log_failed", error=str(e), device_id=command_data.get("device_id"))
            raise

    async def get_commands(self, device_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get command logs for a device from Supabase."""
        try:
            response = (
                self.client.table("command_logs")
                .select("*")
                .eq("device_id", device_id)
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error("commands_get_failed", error=str(e), device_id=device_id)
            return []

    # ── Chat Sessions ────────────────────────────────────────

    async def create_chat_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create chat session in Supabase."""
        try:
            response = self.client.table("chat_sessions").insert(session_data).execute()
            logger.info("chat_session_created", session_id=session_data.get("id"), user_id=session_data.get("user_id"))
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("chat_session_create_failed", error=str(e))
            raise

    async def get_chat_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all chat sessions for a user from Supabase."""
        try:
            response = (
                self.client.table("chat_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error("chat_sessions_get_failed", error=str(e), user_id=user_id)
            return []

    async def delete_chat_session(self, session_id: str) -> bool:
        """Delete chat session from Supabase."""
        try:
            self.client.table("chat_sessions").delete().eq("id", session_id).execute()
            logger.info("chat_session_deleted", session_id=session_id)
            return True
        except Exception as e:
            logger.error("chat_session_delete_failed", error=str(e), session_id=session_id)
            return False

    # ── Chat Messages ────────────────────────────────────────

    async def create_chat_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create chat message in Supabase."""
        try:
            response = self.client.table("chat_messages").insert(message_data).execute()
            return response.data[0] if response.data else {}
        except Exception as e:
            logger.error("chat_message_create_failed", error=str(e))
            raise

    async def get_chat_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a chat session from Supabase."""
        try:
            response = (
                self.client.table("chat_messages")
                .select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error("chat_messages_get_failed", error=str(e), session_id=session_id)
            return []


# Singleton instance
supabase_service = SupabaseService()
