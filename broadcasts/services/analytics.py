"""
AeroChat Broadcasts Module — Analytics Service
=================================================
Aggregates broadcast analytics with full database integration.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import text

from ..config import settings
from ..database import get_session
from ..models import BroadcastMetric, BroadcastStats, FunnelStage

logger = logging.getLogger("broadcasts.analytics")


METRIC_COLORS = {
    "sent": "#3b82f6",
    "delivered": "#25D366",
    "read": "#10b981",
    "replied": "#059669",
    "failed": "#ef4444",
}


class BroadcastAnalyticsData:
    """Container for a single broadcast's analytics."""

    def __init__(self, sent_count=0, delivered_count=0, read_count=0, replied_count=0, failed_count=0):
        self.sent_count = sent_count
        self.delivered_count = delivered_count
        self.read_count = read_count
        self.replied_count = replied_count
        self.failed_count = failed_count
        self.metrics: List[BroadcastMetric] = []
        self.funnel: List[FunnelStage] = []
        self._compute_metrics()
        self._compute_funnel()

    def _compute_metrics(self):
        total = self.sent_count + self.failed_count
        self.metrics = [
            BroadcastMetric(
                label="Total Sent", value=self.sent_count, percentage=None,
                color=METRIC_COLORS["sent"], tooltip=None,
            ),
            BroadcastMetric(
                label="Delivered", value=self.delivered_count,
                percentage=self._pct(self.delivered_count, self.sent_count),
                color=METRIC_COLORS["delivered"], tooltip=None,
            ),
            BroadcastMetric(
                label="Read", value=self.read_count,
                percentage=self._pct(self.read_count, self.delivered_count),
                color=METRIC_COLORS["read"],
                tooltip="May undercount — users can disable read receipts",
            ),
            BroadcastMetric(
                label="Replied", value=self.replied_count,
                percentage=self._pct(self.replied_count, self.delivered_count),
                color=METRIC_COLORS["replied"], tooltip=None,
            ),
            BroadcastMetric(
                label="Failed", value=self.failed_count,
                percentage=self._pct(self.failed_count, total),
                color=METRIC_COLORS["failed"], tooltip=None,
            ),
        ]

    def _compute_funnel(self):
        base = max(self.sent_count, 1)
        stages = [
            FunnelStage(label="Sent", count=self.sent_count, color=METRIC_COLORS["sent"], flex=100),
            FunnelStage(label="Delivered", count=self.delivered_count, color=METRIC_COLORS["delivered"],
                        flex=max(1, round(self.delivered_count / base * 100))),
            FunnelStage(label="Read", count=self.read_count, color=METRIC_COLORS["read"],
                        flex=max(1, round(self.read_count / base * 100)) if self.read_count > 0 else 0),
            FunnelStage(label="Replied", count=self.replied_count, color=METRIC_COLORS["replied"],
                        flex=max(1, round(self.replied_count / base * 100)) if self.replied_count > 0 else 0),
            FunnelStage(label="Failed", count=self.failed_count, color=METRIC_COLORS["failed"],
                        flex=max(1, round(self.failed_count / base * 100)) if self.failed_count > 0 else 0),
        ]
        self.funnel = [s for s in stages if s.count > 0 or s.label == "Sent"]

    @staticmethod
    def _pct(numerator: int, denominator: int) -> Optional[float]:
        if denominator == 0:
            return None
        return round(numerator / denominator * 100, 1)


class AnalyticsService:
    """Service for computing broadcast analytics from MySQL."""

    # =========================================
    # Per-Broadcast Analytics
    # =========================================

    async def get_broadcast_analytics(self, broadcast_id: str) -> BroadcastAnalyticsData:
        """Compute analytics for a single broadcast from recipient records."""
        counts = await self._get_status_counts(broadcast_id)
        return BroadcastAnalyticsData(
            sent_count=counts["sent"],
            delivered_count=counts["delivered"],
            read_count=counts["read"],
            replied_count=counts["replied"],
            failed_count=counts["failed"],
        )

    async def _get_status_counts(self, broadcast_id: str) -> dict:
        """
        Query cumulative recipient status counts.

        Statuses represent the LATEST state. Counting is cumulative:
        - sent = total - failed (anything not failed was at least sent)
        - delivered = those at delivered, read, or replied
        - read = those at read or replied
        - replied = those at replied
        - failed = those at failed
        """
        async with get_session() as session:
            query = text(f"""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status IN ('delivered','read','replied') THEN 1 ELSE 0 END) as delivered,
                    SUM(CASE WHEN status IN ('read','replied') THEN 1 ELSE 0 END) as read_count,
                    SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END) as replied
                FROM {settings.TABLE_BROADCAST_RECIPIENTS}
                WHERE broadcast_id = :bid
            """)
            result = await session.execute(query, {"bid": broadcast_id})
            row = result.fetchone()

            if not row or row.total == 0:
                return {"sent": 0, "delivered": 0, "read": 0, "replied": 0, "failed": 0}

            failed = row.failed or 0
            return {
                "sent": (row.total or 0) - failed,
                "delivered": row.delivered or 0,
                "read": row.read_count or 0,
                "replied": row.replied or 0,
                "failed": failed,
            }

    # =========================================
    # List-Level Aggregate Stats
    # =========================================

    async def get_list_stats(self) -> BroadcastStats:
        """Compute aggregate stats with month-over-month comparison."""
        now = datetime.utcnow()

        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            current_end = current_start.replace(year=now.year + 1, month=1)
        else:
            current_end = current_start.replace(month=now.month + 1)

        if current_start.month == 1:
            prev_start = current_start.replace(year=current_start.year - 1, month=12)
        else:
            prev_start = current_start.replace(month=current_start.month - 1)
        prev_end = current_start

        current = await self._get_period_stats(current_start, current_end)
        previous = await self._get_period_stats(prev_start, prev_end)

        return BroadcastStats(
            total_sent=current["total_sent"],
            total_sent_change_pct=self._change_pct(current["total_sent"], previous["total_sent"]),
            avg_delivery_rate=current["avg_delivery_rate"],
            avg_delivery_rate_change=self._change_diff(
                current["avg_delivery_rate"], previous["avg_delivery_rate"]
            ),
            avg_read_rate=current["avg_read_rate"],
            avg_read_rate_change=self._change_diff(
                current["avg_read_rate"], previous["avg_read_rate"]
            ),
            avg_reply_rate=current["avg_reply_rate"],
            avg_reply_rate_change=self._change_diff(
                current["avg_reply_rate"], previous["avg_reply_rate"]
            ),
        )

    async def _get_period_stats(self, start: datetime, end: datetime) -> dict:
        """Get aggregate stats for a time period."""
        async with get_session() as session:
            query = text(f"""
                SELECT
                    COUNT(DISTINCT b.id) as broadcast_count,
                    COALESCE(SUM(b.recipient_count), 0) as total_sent,
                    AVG(sub.delivery_rate) as avg_delivery_rate,
                    AVG(sub.read_rate) as avg_read_rate,
                    AVG(sub.reply_rate) as avg_reply_rate
                FROM {settings.TABLE_BROADCASTS} b
                LEFT JOIN (
                    SELECT
                        broadcast_id,
                        SUM(CASE WHEN status IN ('delivered','read','replied') THEN 1 ELSE 0 END)
                            / NULLIF(COUNT(*), 0) * 100 as delivery_rate,
                        SUM(CASE WHEN status IN ('read','replied') THEN 1 ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN status IN ('delivered','read','replied') THEN 1 ELSE 0 END), 0) * 100 as read_rate,
                        SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END)
                            / NULLIF(SUM(CASE WHEN status IN ('delivered','read','replied') THEN 1 ELSE 0 END), 0) * 100 as reply_rate
                    FROM {settings.TABLE_BROADCAST_RECIPIENTS}
                    GROUP BY broadcast_id
                ) sub ON b.id = sub.broadcast_id
                WHERE b.status = 'sent'
                AND b.sent_at >= :start_dt
                AND b.sent_at < :end_dt
            """)
            result = await session.execute(query, {"start_dt": start, "end_dt": end})
            row = result.fetchone()

            if not row or row.broadcast_count == 0:
                return {
                    "total_sent": 0,
                    "avg_delivery_rate": None,
                    "avg_read_rate": None,
                    "avg_reply_rate": None,
                }

            return {
                "total_sent": row.total_sent or 0,
                "avg_delivery_rate": round(float(row.avg_delivery_rate), 1) if row.avg_delivery_rate else None,
                "avg_read_rate": round(float(row.avg_read_rate), 1) if row.avg_read_rate else None,
                "avg_reply_rate": round(float(row.avg_reply_rate), 1) if row.avg_reply_rate else None,
            }

    # =========================================
    # Actual Cost Calculation
    # =========================================

    async def compute_actual_cost(self, broadcast_id: str) -> float:
        """Compute actual cost from per-recipient country rates."""
        country_counts = await self._get_recipient_country_counts(broadcast_id)

        total_cost = 0.0
        for country_code, count in country_counts.items():
            rate = settings.COST_RATES_BY_COUNTRY.get(
                (country_code or "").upper(),
                settings.DEFAULT_COST_PER_MESSAGE_USD,
            )
            total_cost += rate * count

        return round(total_cost, 2)

    async def _get_recipient_country_counts(self, broadcast_id: str) -> dict:
        """Get recipient counts grouped by country code."""
        async with get_session() as session:
            query = text(f"""
                SELECT
                    COALESCE(br.country_code, c.country_code, 'UNKNOWN') as cc,
                    COUNT(*) as cnt
                FROM {settings.TABLE_BROADCAST_RECIPIENTS} br
                LEFT JOIN {settings.TABLE_CONTACTS} c ON br.contact_id = c.id
                WHERE br.broadcast_id = :bid
                AND br.status != 'failed'
                GROUP BY cc
            """)
            result = await session.execute(query, {"bid": broadcast_id})
            rows = result.fetchall()

            return {row.cc: row.cnt for row in rows}

    # =========================================
    # Utility
    # =========================================

    @staticmethod
    def _change_pct(current: int, previous: int) -> Optional[float]:
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 1)

    @staticmethod
    def _change_diff(current: Optional[float], previous: Optional[float]) -> Optional[float]:
        if current is None or previous is None:
            return None
        return round(current - previous, 1)
