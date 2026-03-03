"""
AeroChat Broadcasts Module — Configuration
============================================
All external dependencies and environment-specific values live here.
Developer fills in these values to connect to the AeroChat backend.

Usage:
    from broadcasts.config import settings
    token = settings.META_ACCESS_TOKEN
"""

from pydantic_settings import BaseSettings
from typing import Optional


class BroadcastSettings(BaseSettings):

    # =========================================
    # Meta / WhatsApp Cloud API
    # =========================================

    # System User token with whatsapp_business_messaging permission
    META_ACCESS_TOKEN: str = "PLACEHOLDER_META_ACCESS_TOKEN"

    # WhatsApp Business Account ID
    META_WABA_ID: str = "PLACEHOLDER_WABA_ID"

    # Phone Number ID (the number messages are sent FROM)
    META_PHONE_NUMBER_ID: str = "PLACEHOLDER_PHONE_NUMBER_ID"

    # Meta Graph API version
    META_API_VERSION: str = "v21.0"

    # Base URL (no trailing slash)
    META_API_BASE_URL: str = "https://graph.facebook.com"

    # Webhook verification token (you define this, Meta must match it)
    META_WEBHOOK_VERIFY_TOKEN: str = "PLACEHOLDER_WEBHOOK_VERIFY_TOKEN"

    # App secret for webhook signature verification (X-Hub-Signature-256)
    META_APP_SECRET: str = "PLACEHOLDER_APP_SECRET"

    # =========================================
    # Database
    # =========================================

    # Async connection URL
    # e.g. "postgresql+asyncpg://user:pass@localhost:5432/aerochat"
    DATABASE_URL: str = "mysql+aiomysql://root:@localhost:3306/aerochat"

    # Table names — adjust to match your schema
    DB_TABLE_BROADCASTS: str = "broadcasts"
    DB_TABLE_BROADCAST_RECIPIENTS: str = "broadcast_recipients"
    DB_TABLE_CONTACTS: str = "contacts"
    DB_TABLE_SEGMENTS: str = "segments"
    DB_TABLE_SEGMENT_MEMBERS: str = "segment_members"
    DB_TABLE_TEMPLATES_CACHE: str = "wa_templates_cache"
    DB_TABLE_WEBHOOK_EVENTS: str = "wa_webhook_events"

    # =========================================
    # Broadcast Sending
    # =========================================

    # Max concurrent Meta API requests (Meta rate limit ~80 msg/sec for Business)
    SEND_CONCURRENCY_LIMIT: int = 40

    # Delay between batches (seconds)
    SEND_BATCH_DELAY: float = 1.0

    # Retry config for failed sends
    SEND_MAX_RETRIES: int = 3
    SEND_RETRY_BACKOFF: float = 2.0  # exponential: base * 2^attempt
    SEND_REQUEST_TIMEOUT: float = 30.0

    # =========================================
    # Scheduling
    # =========================================

    DEFAULT_TIMEZONE: str = "Asia/Singapore"
    SCHEDULER_POLL_INTERVAL: int = 30  # seconds
    SCHEDULER_PREPARATION_LEAD: int = 300  # start preparing 5 min before

    # =========================================
    # Webhook Processing
    # =========================================

    # Time window to attribute inbound replies to a broadcast
    REPLY_ATTRIBUTION_WINDOW: int = 86400  # 24 hours

    WEBHOOK_BATCH_SIZE: int = 100

    # =========================================
    # Cost Estimation
    # =========================================

    # Default per-message rates (USD) when country is unknown
    DEFAULT_MARKETING_RATE: float = 0.05
    DEFAULT_UTILITY_RATE: float = 0.00  # Free within 24hr window

    # Country-specific rates (ISO 3166-1 alpha-2 → USD per message)
    # Populate from: https://developers.facebook.com/docs/whatsapp/pricing
    COST_RATES_BY_COUNTRY: dict = {
        "US": 0.025,
        "GB": 0.035,
        "SG": 0.050,
        "IN": 0.012,
        "BR": 0.025,
    }

    # =========================================
    # CSV Import
    # =========================================

    CSV_MAX_ROWS: int = 50000
    CSV_MAX_FILE_SIZE: int = 5 * 1024 * 1024  # 5MB

    # Auto-detected phone column names (case-insensitive)
    CSV_PHONE_COLUMN_NAMES: list = [
        "phone", "phone_number", "mobile", "whatsapp",
        "tel", "telephone", "number", "contact",
    ]

    # =========================================
    # Internal API
    # =========================================

    API_PREFIX: str = "/api/broadcasts"

    # Connect to AeroChat's existing auth system
    INTERNAL_API_KEY: Optional[str] = None

    # =========================================
    # Logging
    # =========================================

    LOG_LEVEL: str = "INFO"
    LOG_META_API_BODIES: bool = False  # Verbose — disable in prod

    # =========================================
    # Aliases (services use these names)
    # =========================================

    @property
    def TABLE_BROADCASTS(self) -> str:
        return self.DB_TABLE_BROADCASTS

    @property
    def TABLE_BROADCAST_RECIPIENTS(self) -> str:
        return self.DB_TABLE_BROADCAST_RECIPIENTS

    @property
    def TABLE_CONTACTS(self) -> str:
        return self.DB_TABLE_CONTACTS

    @property
    def TABLE_SEGMENTS(self) -> str:
        return self.DB_TABLE_SEGMENTS

    @property
    def TABLE_SEGMENT_MEMBERS(self) -> str:
        return self.DB_TABLE_SEGMENT_MEMBERS

    @property
    def DISPATCH_CONCURRENCY(self) -> int:
        return self.SEND_CONCURRENCY_LIMIT

    @property
    def DISPATCH_BATCH_DELAY(self) -> float:
        return self.SEND_BATCH_DELAY

    @property
    def DISPATCH_MAX_RETRIES(self) -> int:
        return self.SEND_MAX_RETRIES

    @property
    def DISPATCH_RETRY_DELAY(self) -> float:
        return self.SEND_RETRY_BACKOFF

    @property
    def DISPATCH_TIMEOUT(self) -> float:
        return self.SEND_REQUEST_TIMEOUT

    @property
    def DEFAULT_COST_PER_MESSAGE_USD(self) -> float:
        return self.DEFAULT_MARKETING_RATE

    @property
    def CSV_PHONE_COLUMN(self) -> str:
        return self.CSV_PHONE_COLUMN_NAMES[0]

    DEFAULT_PAGE_SIZE: int = 25
    MAX_PAGE_SIZE: int = 100
    TEMPLATE_CACHE_TTL: int = 300  # 5 minutes

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Singleton — import this everywhere
settings = BroadcastSettings()
