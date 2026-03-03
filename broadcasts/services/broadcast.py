"""
AeroChat Broadcasts Module — Broadcast Service
=================================================
Core orchestration service with full database integration.
"""

import asyncio
import csv
import io
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select, insert, update, delete, func, and_, or_, text
from sqlalchemy.dialects.mysql import insert as mysql_insert

from ..config import settings
from ..database import (
    get_session,
    broadcasts_table,
    recipients_table,
    csv_uploads_table,
    metadata,
)
from ..models import (
    BroadcastCreate,
    BroadcastUpdate,
    BroadcastSummary,
    BroadcastDetail,
    BroadcastListResponse,
    BroadcastStatus,
    BroadcastDispatchResult,
    AudienceType,
    ScheduleType,
    RecipientStatus,
    CostEstimate,
    CSVUploadResult,
    Contact,
    Segment,
    DispatchResult,
)
from .meta_api import MetaAPIService, MessageSendError

logger = logging.getLogger("broadcasts.service")

# Reference to existing AeroChat tables (adjust names in config.py)
# These use text() for raw table/column references since the tables
# are defined elsewhere in your schema.
CONTACTS_TABLE = settings.TABLE_CONTACTS
SEGMENTS_TABLE = settings.TABLE_SEGMENTS
SEGMENT_MEMBERS_TABLE = settings.TABLE_SEGMENT_MEMBERS


class BroadcastService:
    """Core service for broadcast operations with MySQL database integration."""

    def __init__(self):
        self.meta = MetaAPIService()

    # =========================================
    # Segments / Audience Queries
    # =========================================

    async def get_segments(self) -> List[Segment]:
        """Fetch all audience segments with contact counts."""
        async with get_session() as session:
            query = text(f"""
                SELECT s.id, s.name, s.description,
                       COUNT(sm.contact_id) as contact_count
                FROM {SEGMENTS_TABLE} s
                LEFT JOIN {SEGMENT_MEMBERS_TABLE} sm ON s.id = sm.segment_id
                GROUP BY s.id, s.name, s.description
                ORDER BY s.name
            """)
            result = await session.execute(query)
            rows = result.fetchall()

            return [
                Segment(
                    id=row.id,
                    name=row.name,
                    description=row.description,
                    contact_count=row.contact_count or 0,
                )
                for row in rows
            ]

    async def get_total_opted_in_count(self) -> int:
        """Count all contacts with whatsapp_opted_in = True."""
        async with get_session() as session:
            query = text(f"""
                SELECT COUNT(*) as cnt
                FROM {CONTACTS_TABLE}
                WHERE whatsapp_opted_in = 1
                AND phone IS NOT NULL
                AND phone != ''
            """)
            result = await session.execute(query)
            row = result.fetchone()
            return row.cnt if row else 0

    async def _resolve_audience(self, broadcast: BroadcastDetail) -> List[Contact]:
        """Resolve audience to a list of contacts. Filters to opted-in only."""
        if broadcast.audience_type == AudienceType.ALL_SUBSCRIBERS:
            return await self._get_all_opted_in_contacts()
        elif broadcast.audience_type == AudienceType.SEGMENT:
            segment_id = getattr(broadcast, "segment_id", None)
            return await self._get_segment_contacts(segment_id)
        elif broadcast.audience_type == AudienceType.CSV_UPLOAD:
            csv_file_id = getattr(broadcast, "csv_file_id", None)
            return await self._get_csv_contacts(csv_file_id)
        else:
            raise ValueError(f"Unknown audience type: {broadcast.audience_type}")

    async def _get_all_opted_in_contacts(self) -> List[Contact]:
        """Fetch all WhatsApp opted-in contacts."""
        async with get_session() as session:
            query = text(f"""
                SELECT id, name, phone, email, country_code
                FROM {CONTACTS_TABLE}
                WHERE whatsapp_opted_in = 1
                AND phone IS NOT NULL
                AND phone != ''
            """)
            result = await session.execute(query)
            rows = result.fetchall()

            return [
                Contact(
                    id=row.id,
                    name=row.name,
                    phone=row.phone,
                    email=getattr(row, "email", None),
                    whatsapp_opted_in=True,
                    country_code=getattr(row, "country_code", None),
                )
                for row in rows
            ]

    async def _get_segment_contacts(self, segment_id: str) -> List[Contact]:
        """Fetch opted-in contacts for a segment."""
        if not segment_id:
            raise ValueError("segment_id is required for segment audience")

        async with get_session() as session:
            query = text(f"""
                SELECT c.id, c.name, c.phone, c.email, c.country_code
                FROM {CONTACTS_TABLE} c
                JOIN {SEGMENT_MEMBERS_TABLE} sm ON c.id = sm.contact_id
                WHERE sm.segment_id = :segment_id
                AND c.whatsapp_opted_in = 1
                AND c.phone IS NOT NULL
                AND c.phone != ''
            """)
            result = await session.execute(query, {"segment_id": segment_id})
            rows = result.fetchall()

            return [
                Contact(
                    id=row.id,
                    name=row.name,
                    phone=row.phone,
                    email=getattr(row, "email", None),
                    whatsapp_opted_in=True,
                    country_code=getattr(row, "country_code", None),
                )
                for row in rows
            ]

    async def _get_csv_contacts(self, csv_file_id: str) -> List[Contact]:
        """Fetch contacts from a parsed CSV upload."""
        if not csv_file_id:
            raise ValueError("csv_file_id is required for CSV audience")

        async with get_session() as session:
            # Get stored phone list from CSV upload
            query = select(csv_uploads_table.c.phones).where(
                csv_uploads_table.c.id == csv_file_id
            )
            result = await session.execute(query)
            row = result.fetchone()

            if not row or not row.phones:
                raise ValueError(f"CSV upload {csv_file_id} not found or empty")

            phones = row.phones  # JSON array of phone strings

            # Cross-reference with contacts table for names and country codes
            # Phones not in contacts table get minimal Contact objects
            contacts = []
            phone_set = set(phones)

            # Batch lookup existing contacts
            if phone_set:
                placeholders = ",".join([":p" + str(i) for i in range(len(phones))])
                params = {f"p{i}": p for i, p in enumerate(phones)}
                existing_query = text(f"""
                    SELECT id, name, phone, email, country_code, whatsapp_opted_in
                    FROM {CONTACTS_TABLE}
                    WHERE phone IN ({placeholders})
                """)
                result = await session.execute(existing_query, params)
                existing_rows = result.fetchall()

                found_phones = set()
                for row in existing_rows:
                    # Only include if opted in
                    if row.whatsapp_opted_in:
                        contacts.append(Contact(
                            id=row.id,
                            name=row.name,
                            phone=row.phone,
                            whatsapp_opted_in=True,
                            country_code=getattr(row, "country_code", None),
                        ))
                    found_phones.add(row.phone)

                # For phones not in contacts table, create minimal entries
                # Note: These won't have opted-in status verified
                for phone in phone_set - found_phones:
                    contacts.append(Contact(
                        id=str(uuid.uuid4()),
                        name=None,
                        phone=phone,
                        whatsapp_opted_in=True,  # Assumed from CSV upload
                        country_code=None,
                    ))

            return contacts

    # =========================================
    # CSV Upload
    # =========================================

    async def parse_csv_upload(self, file_content: bytes, filename: str) -> CSVUploadResult:
        """Parse and validate a CSV file of phone numbers."""
        file_id = str(uuid.uuid4())
        errors: List[str] = []

        try:
            text_content = file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text_content = file_content.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError("Unable to decode CSV file. Please use UTF-8 encoding.")

        reader = csv.DictReader(io.StringIO(text_content))

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header row.")

        phone_col = None
        for col in reader.fieldnames:
            if col.strip().lower() == settings.CSV_PHONE_COLUMN.lower():
                phone_col = col
                break

        if phone_col is None:
            available = ", ".join(reader.fieldnames[:10])
            raise ValueError(
                f"CSV must contain a '{settings.CSV_PHONE_COLUMN}' column. "
                f"Found columns: {available}"
            )

        valid_phones: List[str] = []
        invalid_count = 0
        seen: set = set()
        duplicate_count = 0
        total_rows = 0

        for i, row in enumerate(reader):
            if i >= settings.CSV_MAX_ROWS:
                errors.append(f"CSV exceeds maximum of {settings.CSV_MAX_ROWS:,} rows.")
                break

            total_rows += 1
            raw_phone = (row.get(phone_col) or "").strip()
            if not raw_phone:
                continue

            normalized = re.sub(r"[\s\-\(\)\.]+", "", raw_phone)

            if not re.match(r"^\+?\d{7,15}$", normalized):
                invalid_count += 1
                if invalid_count <= 5:
                    errors.append(f"Row {total_rows}: Invalid phone number '{raw_phone}'")
                continue

            if not normalized.startswith("+"):
                invalid_count += 1
                if invalid_count <= 5:
                    errors.append(f"Row {total_rows}: Missing country code for '{raw_phone}'")
                continue

            if normalized in seen:
                duplicate_count += 1
                continue

            seen.add(normalized)
            valid_phones.append(normalized)

        if invalid_count > 5:
            errors.append(f"... and {invalid_count - 5} more invalid numbers")

        csv_result = CSVUploadResult(
            file_id=file_id,
            total_rows=total_rows,
            valid_phones=len(valid_phones),
            invalid_phones=invalid_count,
            duplicate_phones=duplicate_count,
            phones=valid_phones,
            errors=errors,
        )

        # Store in database
        async with get_session() as session:
            await session.execute(
                insert(csv_uploads_table).values(
                    id=file_id,
                    filename=filename,
                    total_rows=total_rows,
                    valid_phones=len(valid_phones),
                    invalid_phones=invalid_count,
                    duplicate_phones=duplicate_count,
                    phones=valid_phones,
                    errors=errors,
                )
            )
            await session.commit()

        logger.info(f"CSV upload {file_id}: {len(valid_phones)} valid phones from '{filename}'")
        return csv_result

    # =========================================
    # Broadcast CRUD
    # =========================================

    async def list_broadcasts(
        self,
        status: Optional[BroadcastStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> BroadcastListResponse:
        """List broadcasts with optional filters and pagination."""
        async with get_session() as session:
            # Base query
            where_clauses = []
            if status:
                where_clauses.append(broadcasts_table.c.status == status.value)
            if search:
                where_clauses.append(broadcasts_table.c.campaign_name.ilike(f"%{search}%"))

            where = and_(*where_clauses) if where_clauses else True

            # Count total
            count_query = select(func.count()).select_from(broadcasts_table).where(where)
            count_result = await session.execute(count_query)
            total = count_result.scalar() or 0

            # Fetch page
            offset = (page - 1) * page_size
            data_query = (
                select(broadcasts_table)
                .where(where)
                .order_by(broadcasts_table.c.created_at.desc())
                .limit(page_size)
                .offset(offset)
            )
            data_result = await session.execute(data_query)
            rows = data_result.fetchall()

            broadcasts = []
            for row in rows:
                # Get delivery stats for each broadcast
                stats = await self._get_broadcast_quick_stats(session, row.id)

                broadcasts.append(
                    BroadcastSummary(
                        id=row.id,
                        campaign_name=row.campaign_name,
                        template_name=row.template_name,
                        status=BroadcastStatus(row.status),
                        audience_type=AudienceType(row.audience_type),
                        audience_label=row.audience_label,
                        recipient_count=row.recipient_count or 0,
                        delivered_count=stats["delivered"],
                        delivered_pct=stats["delivered_pct"],
                        read_count=stats["read"],
                        read_pct=stats["read_pct"],
                        sent_at=row.sent_at,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
                )

            total_pages = max(1, -(-total // page_size))  # Ceiling division

            return BroadcastListResponse(
                broadcasts=broadcasts,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )

    async def _get_broadcast_quick_stats(self, session, broadcast_id: str) -> dict:
        """Get quick delivery/read stats for list view."""
        query = text(f"""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('delivered','read','replied') THEN 1 ELSE 0 END) as delivered,
                SUM(CASE WHEN status IN ('read','replied') THEN 1 ELSE 0 END) as read_count
            FROM {settings.TABLE_BROADCAST_RECIPIENTS}
            WHERE broadcast_id = :bid
            AND status != 'pending'
        """)
        result = await session.execute(query, {"bid": broadcast_id})
        row = result.fetchone()

        if not row or row.total == 0:
            return {"delivered": 0, "delivered_pct": None, "read": 0, "read_pct": None}

        total_sent = row.total
        delivered = row.delivered or 0
        read_count = row.read_count or 0

        return {
            "delivered": delivered,
            "delivered_pct": round(delivered / total_sent * 100, 1) if total_sent > 0 else None,
            "read": read_count,
            "read_pct": round(read_count / delivered * 100, 1) if delivered > 0 else None,
        }

    async def get_broadcast(self, broadcast_id: str) -> Optional[BroadcastDetail]:
        """Fetch a single broadcast by ID."""
        async with get_session() as session:
            query = select(broadcasts_table).where(broadcasts_table.c.id == broadcast_id)
            result = await session.execute(query)
            row = result.fetchone()

            if not row:
                return None

            return BroadcastDetail(
                id=row.id,
                campaign_name=row.campaign_name,
                template_name=row.template_name,
                template_category=row.template_category,
                status=BroadcastStatus(row.status),
                audience_type=AudienceType(row.audience_type),
                audience_label=row.audience_label,
                audience_count=row.recipient_count or 0,
                schedule_type=ScheduleType(row.schedule_type) if row.schedule_type else ScheduleType.NOW,
                scheduled_at=row.scheduled_at,
                timezone=row.timezone,
                sent_at=row.sent_at,
                estimated_cost=row.estimated_cost,
                actual_cost=row.actual_cost,
                message_preview=row.message_preview,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def create_broadcast(self, data: BroadcastCreate) -> BroadcastSummary:
        """Create a new broadcast as a draft."""
        broadcast_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Resolve audience label
        audience_label = "All Subscribers"
        if data.audience_type == AudienceType.SEGMENT and data.segment_id:
            async with get_session() as session:
                seg_query = text(f"SELECT name FROM {SEGMENTS_TABLE} WHERE id = :sid")
                seg_result = await session.execute(seg_query, {"sid": data.segment_id})
                seg_row = seg_result.fetchone()
                if seg_row:
                    audience_label = seg_row.name
        elif data.audience_type == AudienceType.CSV_UPLOAD:
            audience_label = "CSV Upload"

        async with get_session() as session:
            await session.execute(
                insert(broadcasts_table).values(
                    id=broadcast_id,
                    campaign_name=data.campaign_name,
                    template_name=data.template_name,
                    template_language=data.template_language,
                    status="draft",
                    audience_type=data.audience_type.value,
                    segment_id=data.segment_id,
                    csv_file_id=data.csv_file_id,
                    audience_label=audience_label,
                    schedule_type=data.schedule_type.value,
                    scheduled_at=data.scheduled_at,
                    timezone=data.timezone,
                    template_variables=data.template_variables,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()

        logger.info(f"Created broadcast draft: {broadcast_id} - '{data.campaign_name}'")

        return BroadcastSummary(
            id=broadcast_id,
            campaign_name=data.campaign_name,
            template_name=data.template_name,
            status=BroadcastStatus.DRAFT,
            audience_type=data.audience_type,
            audience_label=audience_label,
            recipient_count=0,
            created_at=now,
            updated_at=now,
        )

    async def update_broadcast(self, broadcast_id: str, data: BroadcastUpdate) -> BroadcastSummary:
        """Update a draft or scheduled broadcast."""
        update_values = {"updated_at": datetime.now(timezone.utc)}

        # Only include non-None fields
        for field in ["campaign_name", "template_name", "template_language",
                       "schedule_type", "scheduled_at", "timezone", "template_variables",
                       "segment_id", "csv_file_id"]:
            value = getattr(data, field, None)
            if value is not None:
                if hasattr(value, "value"):  # Enum
                    update_values[field] = value.value
                else:
                    update_values[field] = value

        if data.audience_type is not None:
            update_values["audience_type"] = data.audience_type.value

        async with get_session() as session:
            await session.execute(
                update(broadcasts_table)
                .where(broadcasts_table.c.id == broadcast_id)
                .values(**update_values)
            )
            await session.commit()

        return await self._get_broadcast_summary(broadcast_id)

    async def delete_broadcast(self, broadcast_id: str) -> None:
        """Delete a draft broadcast and its recipients."""
        async with get_session() as session:
            # Recipients cascade-deleted via FK
            await session.execute(
                delete(broadcasts_table).where(broadcasts_table.c.id == broadcast_id)
            )
            await session.commit()

        logger.info(f"Deleted broadcast: {broadcast_id}")

    async def duplicate_broadcast(self, broadcast_id: str) -> BroadcastSummary:
        """Duplicate a broadcast as a new draft."""
        original = await self.get_broadcast(broadcast_id)
        if not original:
            raise ValueError("Broadcast not found")

        new_data = BroadcastCreate(
            campaign_name=f"{original.campaign_name} (Copy)",
            template_name=original.template_name,
            audience_type=original.audience_type,
            segment_id=getattr(original, "segment_id", None),
            schedule_type=ScheduleType.NOW,
        )
        return await self.create_broadcast(new_data)

    async def cancel_broadcast(self, broadcast_id: str) -> None:
        """Cancel a scheduled broadcast."""
        async with get_session() as session:
            await session.execute(
                update(broadcasts_table)
                .where(broadcasts_table.c.id == broadcast_id)
                .values(status="cancelled", updated_at=datetime.now(timezone.utc))
            )
            await session.commit()

        logger.info(f"Cancelled broadcast: {broadcast_id}")

    async def _get_broadcast_summary(self, broadcast_id: str) -> BroadcastSummary:
        """Helper to fetch a broadcast as a summary."""
        async with get_session() as session:
            query = select(broadcasts_table).where(broadcasts_table.c.id == broadcast_id)
            result = await session.execute(query)
            row = result.fetchone()
            if not row:
                raise ValueError("Broadcast not found")

            return BroadcastSummary(
                id=row.id,
                campaign_name=row.campaign_name,
                template_name=row.template_name,
                status=BroadcastStatus(row.status),
                audience_type=AudienceType(row.audience_type),
                audience_label=row.audience_label,
                recipient_count=row.recipient_count or 0,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    # =========================================
    # Cost Estimation
    # =========================================

    async def estimate_cost(self, broadcast_id: str) -> CostEstimate:
        """Estimate Meta messaging cost based on audience and country rates."""
        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            raise ValueError("Broadcast not found")

        contacts = await self._resolve_audience(broadcast)
        recipient_count = len(contacts)

        if recipient_count == 0:
            return CostEstimate(
                recipient_count=0,
                cost_per_message=settings.DEFAULT_COST_PER_MESSAGE_USD,
                total_estimated_cost=0.0,
            )

        total_cost = 0.0
        for contact in contacts:
            country = contact.country_code or ""
            rate = settings.COST_RATES_BY_COUNTRY.get(
                country.upper(), settings.DEFAULT_COST_PER_MESSAGE_USD
            )
            total_cost += rate

        avg_cost = total_cost / recipient_count

        return CostEstimate(
            recipient_count=recipient_count,
            cost_per_message=round(avg_cost, 4),
            total_estimated_cost=round(total_cost, 2),
        )

    # =========================================
    # Dispatch Orchestration
    # =========================================

    async def send_broadcast(self, broadcast_id: str) -> BroadcastDispatchResult:
        """Send or schedule a broadcast."""
        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            raise ValueError("Broadcast not found")

        if broadcast.schedule_type == ScheduleType.SCHEDULED and broadcast.scheduled_at:
            await self._mark_as_scheduled(broadcast_id, broadcast.scheduled_at)
            return BroadcastDispatchResult(
                broadcast_id=broadcast_id,
                total_attempted=0, total_sent=0, total_failed=0,
                duration_seconds=0.0,
            )

        return await self._execute_dispatch(broadcast_id)

    async def _mark_as_scheduled(self, broadcast_id: str, scheduled_at: datetime) -> None:
        """Mark a broadcast as scheduled."""
        async with get_session() as session:
            await session.execute(
                update(broadcasts_table)
                .where(broadcasts_table.c.id == broadcast_id)
                .values(
                    status="scheduled",
                    scheduled_at=scheduled_at,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()
        logger.info(f"Broadcast {broadcast_id} scheduled for {scheduled_at}")

    async def _execute_dispatch(self, broadcast_id: str) -> BroadcastDispatchResult:
        """Execute actual message dispatch."""
        start_time = time.time()

        broadcast = await self.get_broadcast(broadcast_id)
        if not broadcast:
            raise ValueError("Broadcast not found")

        contacts = await self._resolve_audience(broadcast)
        if not contacts:
            raise ValueError("No recipients found")

        logger.info(f"Dispatching broadcast {broadcast_id} to {len(contacts)} recipients")

        # Update status + recipient count
        await self._update_status(broadcast_id, BroadcastStatus.SENDING)
        await self._update_recipient_count(broadcast_id, len(contacts))

        # Dispatch with concurrency control
        results: List[DispatchResult] = []
        semaphore = asyncio.Semaphore(settings.DISPATCH_CONCURRENCY)

        async def send_one(contact: Contact) -> DispatchResult:
            async with semaphore:
                return await self._send_to_contact(broadcast, contact)

        batch_size = settings.DISPATCH_CONCURRENCY
        for i in range(0, len(contacts), batch_size):
            batch = contacts[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[send_one(c) for c in batch],
                return_exceptions=True,
            )
            for r in batch_results:
                if isinstance(r, Exception):
                    logger.error(f"Dispatch error: {r}")
                    continue
                results.append(r)

            if i + batch_size < len(contacts):
                await asyncio.sleep(settings.DISPATCH_BATCH_DELAY)

        # Store results
        await self._store_recipient_results(broadcast_id, results)

        total_sent = sum(1 for r in results if r.status == RecipientStatus.SENT)
        total_failed = sum(1 for r in results if r.status == RecipientStatus.FAILED)
        duration = time.time() - start_time

        final_status = BroadcastStatus.SENT if total_sent > 0 else BroadcastStatus.FAILED
        await self._update_status(broadcast_id, final_status)
        await self._update_sent_at(broadcast_id, datetime.now(timezone.utc))

        logger.info(f"Broadcast {broadcast_id}: {total_sent} sent, {total_failed} failed, {duration:.1f}s")

        return BroadcastDispatchResult(
            broadcast_id=broadcast_id,
            total_attempted=len(results),
            total_sent=total_sent,
            total_failed=total_failed,
            duration_seconds=round(duration, 2),
            results=results,
        )

    async def _send_to_contact(self, broadcast: BroadcastDetail, contact: Contact) -> DispatchResult:
        """Send to a single contact with retry logic."""
        last_error_code = None
        last_error_message = None

        for attempt in range(1, settings.DISPATCH_MAX_RETRIES + 1):
            try:
                body_params = self._build_body_params(broadcast, contact)
                result = await self.meta.send_template_message(
                    to_phone=contact.phone,
                    template_name=broadcast.template_name,
                    language_code="en",
                    body_params=body_params,
                )

                meta_message_id = None
                messages = result.get("messages", [])
                if messages:
                    meta_message_id = messages[0].get("id")

                return DispatchResult(
                    contact_id=contact.id, phone=contact.phone,
                    meta_message_id=meta_message_id,
                    status=RecipientStatus.SENT,
                    timestamp=datetime.now(timezone.utc),
                )

            except MessageSendError as e:
                last_error_code = e.error_code
                last_error_message = e.error_message
                non_retryable = {"131026", "131047", "131051", "131053"}
                if e.error_code in non_retryable:
                    break
                if attempt < settings.DISPATCH_MAX_RETRIES:
                    delay = settings.DISPATCH_RETRY_DELAY * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

            except Exception as e:
                last_error_code = "UNKNOWN"
                last_error_message = str(e)
                break

        return DispatchResult(
            contact_id=contact.id, phone=contact.phone,
            meta_message_id=None, status=RecipientStatus.FAILED,
            error_code=last_error_code, error_message=last_error_message,
            timestamp=datetime.now(timezone.utc),
        )

    def _build_body_params(self, broadcast: BroadcastDetail, contact: Contact) -> List[str]:
        """Build template variable values for a contact."""
        variables = getattr(broadcast, "template_variables", {}) or {}
        params = [contact.name or "there"]
        for i in range(2, 10):
            key = str(i)
            if key in variables:
                params.append(variables[key])
            else:
                break
        return params

    # =========================================
    # Database Helpers
    # =========================================

    async def _update_status(self, broadcast_id: str, status: BroadcastStatus) -> None:
        async with get_session() as session:
            await session.execute(
                update(broadcasts_table)
                .where(broadcasts_table.c.id == broadcast_id)
                .values(status=status.value, updated_at=datetime.now(timezone.utc))
            )
            await session.commit()

    async def _update_sent_at(self, broadcast_id: str, sent_at: datetime) -> None:
        async with get_session() as session:
            await session.execute(
                update(broadcasts_table)
                .where(broadcasts_table.c.id == broadcast_id)
                .values(sent_at=sent_at, updated_at=datetime.now(timezone.utc))
            )
            await session.commit()

    async def _update_recipient_count(self, broadcast_id: str, count: int) -> None:
        async with get_session() as session:
            await session.execute(
                update(broadcasts_table)
                .where(broadcasts_table.c.id == broadcast_id)
                .values(recipient_count=count, updated_at=datetime.now(timezone.utc))
            )
            await session.commit()

    async def _store_recipient_results(self, broadcast_id: str, results: List[DispatchResult]) -> None:
        """Bulk insert recipient results."""
        if not results:
            return

        async with get_session() as session:
            values = [
                {
                    "id": str(uuid.uuid4()),
                    "broadcast_id": broadcast_id,
                    "contact_id": r.contact_id,
                    "phone": r.phone,
                    "meta_message_id": r.meta_message_id,
                    "status": r.status.value,
                    "error_code": r.error_code,
                    "error_message": r.error_message,
                    "sent_at": r.timestamp if r.status == RecipientStatus.SENT else None,
                    "failed_at": r.timestamp if r.status == RecipientStatus.FAILED else None,
                    "country_code": None,  # Populated from contact if available
                    "created_at": r.timestamp,
                    "updated_at": r.timestamp,
                }
                for r in results
            ]

            # Batch insert (MySQL handles bulk efficiently)
            await session.execute(insert(recipients_table), values)
            await session.commit()

        sent = sum(1 for r in results if r.status == RecipientStatus.SENT)
        failed = sum(1 for r in results if r.status == RecipientStatus.FAILED)
        logger.info(f"Stored {len(results)} recipients for {broadcast_id} ({sent} sent, {failed} failed)")
