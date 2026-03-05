"""
AeroChat Broadcasts Module — Webhook Service
===============================================
Processes incoming webhooks from Meta's WhatsApp Cloud API.
Full database integration for status updates and reply attribution.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, update, and_, text

from ..config import settings
from ..database import get_session, recipients_table, broadcasts_table, status_is_advancement
from ..models import WebhookStatusUpdate, InboundMessage, WebhookEventType, RecipientStatus

logger = logging.getLogger("broadcasts.webhook")


# Map webhook event type to recipient status
EVENT_TO_STATUS = {
    WebhookEventType.SENT: RecipientStatus.SENT,
    WebhookEventType.DELIVERED: RecipientStatus.DELIVERED,
    WebhookEventType.READ: RecipientStatus.READ,
    WebhookEventType.FAILED: RecipientStatus.FAILED,
}

# Map status to its timestamp column
STATUS_TIMESTAMP_COLUMN = {
    "sent": "sent_at",
    "delivered": "delivered_at",
    "read": "read_at",
    "replied": "replied_at",
    "failed": "failed_at",
}


class WebhookService:
    """Service for processing Meta WhatsApp webhooks with database integration."""

    # =========================================
    # Signature Verification
    # =========================================

    def verify_signature(self, body: bytes, signature_header: str) -> bool:
        """Verify webhook HMAC-SHA256 signature."""
        if not signature_header or not signature_header.startswith("sha256="):
            logger.warning("Invalid or missing signature header")
            return False

        received_hash = signature_header[7:]
        expected_hash = hmac.new(
            key=settings.META_APP_SECRET.encode("utf-8"),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(received_hash, expected_hash)
        if not is_valid:
            logger.warning("Webhook signature mismatch")
        return is_valid

    # =========================================
    # Webhook Processing
    # =========================================

    async def process_webhook(self, payload: Dict[str, Any]) -> None:
        """Process a webhook payload from Meta."""
        if payload.get("object") != "whatsapp_business_account":
            return

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue

                value = change.get("value", {})

                statuses = value.get("statuses", [])
                if statuses:
                    updates = self._parse_status_updates(statuses)
                    await self._process_status_updates(updates)

                messages = value.get("messages", [])
                if messages:
                    inbound = self._parse_inbound_messages(messages)
                    await self._process_inbound_messages(inbound)

    # =========================================
    # Status Update Parsing & Processing
    # =========================================

    def _parse_status_updates(self, statuses: List[Dict[str, Any]]) -> List[WebhookStatusUpdate]:
        """Parse raw status objects from Meta webhook."""
        updates = []
        status_map = {
            "sent": WebhookEventType.SENT,
            "delivered": WebhookEventType.DELIVERED,
            "read": WebhookEventType.READ,
            "failed": WebhookEventType.FAILED,
        }

        for status_data in statuses:
            try:
                status_str = status_data.get("status", "").lower()
                event_type = status_map.get(status_str)
                if not event_type:
                    continue

                ts_str = status_data.get("timestamp", "0")
                timestamp = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)

                errors = status_data.get("errors", [])
                error_code = str(errors[0].get("code", "")) if errors else None
                error_title = errors[0].get("title", "") if errors else None

                updates.append(WebhookStatusUpdate(
                    meta_message_id=status_data.get("id", ""),
                    status=event_type,
                    timestamp=timestamp,
                    recipient_phone=status_data.get("recipient_id", ""),
                    error_code=error_code,
                    error_title=error_title,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse status: {e}")

        return updates

    async def _process_status_updates(self, updates: List[WebhookStatusUpdate]) -> None:
        """Process status updates — update recipient records in database."""
        if not updates:
            return

        counts = {}
        for u in updates:
            counts[u.status.value] = counts.get(u.status.value, 0) + 1
        logger.info(f"Processing {len(updates)} status updates: {counts}")

        async with get_session() as session:
            for upd in updates:
                new_status = EVENT_TO_STATUS.get(upd.status)
                if not new_status:
                    continue

                # Fetch current status for this message
                query = select(
                    recipients_table.c.id,
                    recipients_table.c.status,
                ).where(
                    recipients_table.c.meta_message_id == upd.meta_message_id
                )
                result = await session.execute(query)
                row = result.fetchone()

                if not row:
                    logger.debug(f"No recipient found for message {upd.meta_message_id}")
                    continue

                # Check if this is a forward advancement
                current_status = row.status
                if not status_is_advancement(current_status, new_status.value):
                    logger.debug(
                        f"Skipping non-advancement: {current_status} → {new_status.value} "
                        f"for {upd.meta_message_id}"
                    )
                    continue

                # Build update values
                update_values = {
                    "status": new_status.value,
                    "updated_at": upd.timestamp,
                }

                # Set the appropriate timestamp column
                ts_col = STATUS_TIMESTAMP_COLUMN.get(new_status.value)
                if ts_col:
                    update_values[ts_col] = upd.timestamp

                # Add error info for failed status
                if new_status == RecipientStatus.FAILED:
                    update_values["error_code"] = upd.error_code
                    update_values["error_message"] = upd.error_title

                await session.execute(
                    update(recipients_table)
                    .where(recipients_table.c.id == row.id)
                    .values(**update_values)
                )

            await session.commit()

    # =========================================
    # Inbound Message (Reply) Processing
    # =========================================

    def _parse_inbound_messages(self, messages: List[Dict[str, Any]]) -> List[InboundMessage]:
        """Parse inbound messages from Meta webhook."""
        parsed = []
        for msg_data in messages:
            try:
                ts_str = msg_data.get("timestamp", "0")
                timestamp = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)

                msg_type = msg_data.get("type", "text")
                msg_text = None
                if msg_type == "text":
                    msg_text = msg_data.get("text", {}).get("body")

                parsed.append(InboundMessage(
                    meta_message_id=msg_data.get("id", ""),
                    from_phone=msg_data.get("from", ""),
                    timestamp=timestamp,
                    text=msg_text,
                    message_type=msg_type,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse inbound message: {e}")

        return parsed

    async def _process_inbound_messages(self, messages: List[InboundMessage]) -> None:
        """Process inbound messages — attribute replies to broadcasts."""
        if not messages:
            return

        window_start = datetime.utcnow() - timedelta(
            hours=settings.REPLY_ATTRIBUTION_WINDOW_HOURS
        )

        for msg in messages:
            attributed = await self._attribute_reply(msg, window_start)
            if attributed:
                logger.info(f"Reply attributed: {msg.from_phone} → broadcast {attributed}")

            await self._forward_to_conversation_handler(msg)

    async def _attribute_reply(
        self, message: InboundMessage, window_start: datetime
    ) -> Optional[str]:
        """
        Try to attribute an inbound message as a reply to a recent broadcast.
        Returns broadcast_id if attributed, None otherwise.
        """
        async with get_session() as session:
            # Find the most recent broadcast sent to this phone within the window
            query = text(f"""
                SELECT br.id as recipient_id, br.broadcast_id
                FROM {settings.TABLE_BROADCAST_RECIPIENTS} br
                JOIN {settings.TABLE_BROADCASTS} b ON br.broadcast_id = b.id
                WHERE br.phone = :phone
                AND b.status = 'sent'
                AND b.sent_at >= :window_start
                ORDER BY b.sent_at DESC
                LIMIT 1
            """)
            result = await session.execute(query, {
                "phone": message.from_phone,
                "window_start": window_start,
            })
            row = result.fetchone()

            if not row:
                return None

            # Update recipient status to 'replied'
            await session.execute(
                update(recipients_table)
                .where(recipients_table.c.id == row.recipient_id)
                .values(
                    status="replied",
                    replied_at=message.timestamp,
                    updated_at=message.timestamp,
                )
            )
            await session.commit()

            return row.broadcast_id

    async def _forward_to_conversation_handler(self, message: InboundMessage) -> None:
        """
        Forward inbound message to AeroChat's conversation system.

        Replace this with your actual forwarding mechanism:
        - Direct function call if in same process
        - Internal API call: POST {settings.AEROCHAT_API_BASE_URL}/api/conversations/inbound
        - Message queue push (recommended for production)
        """
        # PLACEHOLDER — your developer connects this to AeroChat's conversation handler.
        # Example using httpx:
        #
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     await client.post(
        #         f"{settings.AEROCHAT_API_BASE_URL}/api/conversations/inbound",
        #         json={
        #             "from_phone": message.from_phone,
        #             "text": message.text,
        #             "timestamp": message.timestamp.isoformat(),
        #             "channel": "whatsapp",
        #             "message_type": message.message_type,
        #         },
        #         headers={"X-API-Key": settings.AEROCHAT_INTERNAL_API_KEY},
        #     )

        logger.debug(f"Forward inbound from {message.from_phone} to conversation handler")
