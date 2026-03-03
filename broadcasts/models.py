"""
AeroChat Broadcasts Module — Data Models
==========================================
Pydantic models for API request/response schemas,
database record shapes, and shared enums.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# =========================================
# Enums
# =========================================

class BroadcastStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecipientStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    REPLIED = "replied"
    FAILED = "failed"


class AudienceType(str, Enum):
    ALL = "all"
    ALL_SUBSCRIBERS = "all"
    SEGMENT = "segment"
    CSV = "csv"
    CSV_UPLOAD = "csv"


class ScheduleType(str, Enum):
    NOW = "now"
    SCHEDULED = "scheduled"


class TemplateCategory(str, Enum):
    MARKETING = "marketing"
    UTILITY = "utility"
    AUTHENTICATION = "authentication"


# =========================================
# Templates (from Meta API)
# =========================================

class TemplateButton(BaseModel):
    type: str
    text: str
    url: Optional[str] = None
    phone_number: Optional[str] = None


class TemplateComponent(BaseModel):
    type: str
    format: Optional[str] = None
    text: Optional[str] = None
    buttons: Optional[list[TemplateButton]] = None


class Template(BaseModel):
    id: str
    name: str
    language: str
    category: TemplateCategory
    status: str
    components: list[TemplateComponent] = []
    body_text: Optional[str] = None
    header_format: Optional[str] = None
    button_count: int = 0
    variable_count: int = 0


class TemplateListResponse(BaseModel):
    templates: list[Template]
    count: int = 0
    cached: bool = False
    cached_at: Optional[datetime] = None


# =========================================
# Contacts / Segments
# =========================================

class Contact(BaseModel):
    id: str
    name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    whatsapp_opted_in: bool = False
    country_code: Optional[str] = None

ContactRecord = Contact


class Segment(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    contact_count: int = 0

SegmentRecord = Segment


class SegmentListResponse(BaseModel):
    segments: list[Segment]
    total: int = 0
    total_opted_in: int = 0


# =========================================
# Broadcast CRUD
# =========================================

class BroadcastCreate(BaseModel):
    campaign_name: str = Field(..., min_length=1, max_length=255)
    template_name: str
    template_language: str = "en"
    audience_type: AudienceType
    segment_id: Optional[str] = None
    csv_file_id: Optional[str] = None
    csv_contacts: Optional[list[str]] = None
    schedule_type: ScheduleType = ScheduleType.NOW
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    template_variables: Optional[dict] = None


class BroadcastUpdate(BaseModel):
    campaign_name: Optional[str] = None
    template_name: Optional[str] = None
    template_language: Optional[str] = None
    audience_type: Optional[AudienceType] = None
    segment_id: Optional[str] = None
    csv_file_id: Optional[str] = None
    schedule_type: Optional[ScheduleType] = None
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    template_variables: Optional[dict] = None


class BroadcastSummary(BaseModel):
    id: str
    campaign_name: str
    template_name: Optional[str] = None
    status: BroadcastStatus
    audience_type: AudienceType = AudienceType.ALL
    audience_label: Optional[str] = None
    recipient_count: int = 0
    delivered_count: int = 0
    delivered_pct: Optional[float] = None
    read_count: int = 0
    read_pct: Optional[float] = None
    sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

BroadcastListItem = BroadcastSummary


class BroadcastDetail(BaseModel):
    id: str
    campaign_name: str
    template_name: Optional[str] = None
    template_category: Optional[str] = None
    status: BroadcastStatus
    audience_type: AudienceType = AudienceType.ALL
    audience_label: Optional[str] = None
    audience_count: int = 0
    schedule_type: ScheduleType = ScheduleType.NOW
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    sent_at: Optional[datetime] = None
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    message_preview: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metrics: list = []
    funnel: list = []
    sent_count: int = 0
    delivered_count: int = 0
    read_count: int = 0
    replied_count: int = 0
    failed_count: int = 0

BroadcastRecord = BroadcastDetail


class BroadcastListResponse(BaseModel):
    broadcasts: list[BroadcastSummary]
    total: int
    page: int
    page_size: int
    total_pages: int = 1


# =========================================
# Dispatch
# =========================================

class DispatchResult(BaseModel):
    contact_id: str
    phone: str
    meta_message_id: Optional[str] = None
    status: RecipientStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None


class BroadcastDispatchResult(BaseModel):
    broadcast_id: str
    total_attempted: int = 0
    total_sent: int = 0
    total_failed: int = 0
    duration_seconds: float = 0.0
    results: list[DispatchResult] = []


# =========================================
# Analytics
# =========================================

class BroadcastMetric(BaseModel):
    label: str
    value: int
    percentage: Optional[float] = None
    color: str
    tooltip: Optional[str] = None

MetricCard = BroadcastMetric


class FunnelStage(BaseModel):
    label: str
    count: int
    color: str
    flex: int


class BroadcastAnalytics(BaseModel):
    broadcast_id: str
    total_sent: int = 0
    delivered: int = 0
    delivered_pct: float = 0.0
    read: int = 0
    read_pct: float = 0.0
    replied: int = 0
    replied_pct: float = 0.0
    failed: int = 0
    failed_pct: float = 0.0
    estimated_cost: float = 0.0
    actual_cost: Optional[float] = None

BroadcastDetailResponse = BroadcastAnalytics


class BroadcastStats(BaseModel):
    total_sent: int = 0
    total_sent_change_pct: Optional[float] = None
    avg_delivery_rate: Optional[float] = None
    avg_delivery_rate_change: Optional[float] = None
    avg_read_rate: Optional[float] = None
    avg_read_rate_change: Optional[float] = None
    avg_reply_rate: Optional[float] = None
    avg_reply_rate_change: Optional[float] = None


# =========================================
# Recipients
# =========================================

class RecipientRecord(BaseModel):
    id: str
    broadcast_id: str
    contact_id: Optional[str] = None
    phone_number: str
    status: RecipientStatus = RecipientStatus.PENDING
    meta_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


# =========================================
# Webhooks
# =========================================

class WebhookStatusUpdate(BaseModel):
    meta_message_id: str
    phone_number: str
    status: str
    timestamp: datetime
    error_code: Optional[str] = None
    error_title: Optional[str] = None


class WebhookInboundMessage(BaseModel):
    from_phone: str
    message_id: str
    timestamp: datetime
    text: Optional[str] = None
    message_type: str

InboundMessage = WebhookInboundMessage


class WebhookEventType(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# =========================================
# CSV Import
# =========================================

class CSVUploadResult(BaseModel):
    file_id: str
    total_rows: int
    valid_phones: int
    invalid_phones: int
    duplicate_phones: int
    phones: list[str] = []
    errors: list[str] = []

CSVImportResult = CSVUploadResult


# =========================================
# Cost Estimation
# =========================================

class CostEstimate(BaseModel):
    recipient_count: int = 0
    cost_per_message: float = 0.0
    total_estimated_cost: float = 0.0


# =========================================
# Generic Responses
# =========================================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "OK"


class ErrorResponse(BaseModel):
    success: bool = False
    detail: str = ""
