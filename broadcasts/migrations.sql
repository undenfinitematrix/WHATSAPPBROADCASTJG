-- ============================================
-- AeroChat Broadcasts Module — MySQL Migration
-- ============================================
-- Run this script against your AeroChat MySQL database.
-- It creates 3 new tables. It does NOT modify your existing
-- contacts, segments, or segment_members tables.
--
-- Prerequisites:
--   Your database must already have:
--     - contacts table with: id, name, phone, whatsapp_opted_in, country_code
--     - segments table with: id, name, description
--     - segment_members table with: segment_id, contact_id
--
-- If your existing tables use different names, update the
-- TABLE_* values in config.py to match.
-- ============================================


-- ============================================
-- 1. Broadcasts table
-- ============================================
CREATE TABLE IF NOT EXISTS broadcasts (
    id                  VARCHAR(36)     NOT NULL PRIMARY KEY,
    campaign_name       VARCHAR(200)    NOT NULL,
    template_name       VARCHAR(200)    NULL,
    template_language   VARCHAR(10)     DEFAULT 'en',
    template_category   VARCHAR(20)     NULL        COMMENT 'Marketing, Utility, Authentication',
    status              VARCHAR(20)     NOT NULL    DEFAULT 'draft'
                                        COMMENT 'draft, scheduled, sending, sent, failed, cancelled',
    audience_type       VARCHAR(20)     NOT NULL    DEFAULT 'all'
                                        COMMENT 'all, segment, csv',
    segment_id          VARCHAR(36)     NULL,
    csv_file_id         VARCHAR(36)     NULL,
    audience_label      VARCHAR(200)    NULL        COMMENT 'Human-readable audience description',
    recipient_count     INT             DEFAULT 0,
    schedule_type       VARCHAR(20)     DEFAULT 'now'
                                        COMMENT 'now, schedule',
    scheduled_at        DATETIME        NULL,
    timezone            VARCHAR(50)     NULL,
    sent_at             DATETIME        NULL,
    template_variables  JSON            NULL        COMMENT 'Key-value map for template {{variables}}',
    estimated_cost      DECIMAL(10,2)   NULL,
    actual_cost         DECIMAL(10,2)   NULL,
    message_preview     JSON            NULL        COMMENT 'Cached preview data for detail page',
    created_at          DATETIME        NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_broadcasts_status_created (status, created_at),
    INDEX idx_broadcasts_sent_at (sent_at),
    INDEX idx_broadcasts_campaign_name (campaign_name),
    INDEX idx_broadcasts_scheduled_at (status, scheduled_at)
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='WhatsApp broadcast campaigns';


-- ============================================
-- 2. Broadcast recipients table
-- ============================================
CREATE TABLE IF NOT EXISTS broadcast_recipients (
    id                  VARCHAR(36)     NOT NULL PRIMARY KEY,
    broadcast_id        VARCHAR(36)     NOT NULL,
    contact_id          VARCHAR(36)     NULL        COMMENT 'NULL for CSV-uploaded contacts not in contacts table',
    phone               VARCHAR(20)     NOT NULL,
    meta_message_id     VARCHAR(100)    NULL        COMMENT 'WhatsApp message ID from Meta API',
    status              VARCHAR(20)     NOT NULL    DEFAULT 'pending'
                                        COMMENT 'pending, sent, delivered, read, replied, failed',
    error_code          VARCHAR(50)     NULL,
    error_message       TEXT            NULL,
    sent_at             DATETIME        NULL,
    delivered_at        DATETIME        NULL,
    read_at             DATETIME        NULL,
    replied_at          DATETIME        NULL,
    failed_at           DATETIME        NULL,
    country_code        VARCHAR(5)      NULL        COMMENT 'ISO 3166-1 alpha-2 for cost calculation',
    created_at          DATETIME        NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign key
    CONSTRAINT fk_recipients_broadcast
        FOREIGN KEY (broadcast_id) REFERENCES broadcasts(id)
        ON DELETE CASCADE,

    -- Indexes
    INDEX idx_recipients_broadcast_id (broadcast_id),
    INDEX idx_recipients_meta_message_id (meta_message_id),
    INDEX idx_recipients_phone (phone),
    INDEX idx_recipients_broadcast_status (broadcast_id, status),
    INDEX idx_recipients_status_sent (status, sent_at)
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Per-recipient delivery tracking for broadcasts';


-- ============================================
-- 3. CSV uploads table
-- ============================================
CREATE TABLE IF NOT EXISTS csv_uploads (
    id                  VARCHAR(36)     NOT NULL PRIMARY KEY,
    filename            VARCHAR(255)    NOT NULL,
    total_rows          INT             DEFAULT 0,
    valid_phones        INT             DEFAULT 0,
    invalid_phones      INT             DEFAULT 0,
    duplicate_phones    INT             DEFAULT 0,
    phones              JSON            NULL        COMMENT 'Array of validated phone numbers',
    errors              JSON            NULL        COMMENT 'Array of human-readable error messages',
    created_at          DATETIME        NOT NULL    DEFAULT CURRENT_TIMESTAMP
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
COMMENT='Parsed CSV uploads for broadcast audience';


-- ============================================
-- Verification: Check your existing tables
-- ============================================
-- Run these queries to verify your existing tables have
-- the columns the broadcasts module expects:
--
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
-- WHERE TABLE_NAME = 'contacts'
-- AND COLUMN_NAME IN ('id', 'name', 'phone', 'whatsapp_opted_in', 'country_code');
--
-- If 'whatsapp_opted_in' doesn't exist, add it:
-- ALTER TABLE contacts ADD COLUMN whatsapp_opted_in TINYINT(1) DEFAULT 0;
--
-- If 'country_code' doesn't exist, add it:
-- ALTER TABLE contacts ADD COLUMN country_code VARCHAR(5) NULL;


-- ============================================
-- Optional: Add missing columns to contacts
-- ============================================
-- Uncomment and run these if your contacts table is missing
-- columns the broadcasts module needs:
--
-- ALTER TABLE contacts
--     ADD COLUMN IF NOT EXISTS whatsapp_opted_in TINYINT(1) DEFAULT 0,
--     ADD COLUMN IF NOT EXISTS country_code VARCHAR(5) NULL;
--
-- ALTER TABLE contacts
--     ADD INDEX IF NOT EXISTS idx_contacts_opted_in (whatsapp_opted_in);
