# AeroChat Broadcasts Module — Developer Guide

## Overview

This module powers WhatsApp broadcast messaging for AeroChat merchants. It handles the full lifecycle: creating campaigns, selecting audiences, sending messages via Meta's WhatsApp Cloud API, processing delivery webhooks, and computing analytics.

**Stack:** FastAPI (Python) + Async SQLAlchemy + MySQL + React frontend

**Total:** 10 files, ~114 KB

---

## Architecture

```
React UI (BroadcastsList, BroadcastWizard, BroadcastDetail)
    ↓
api-client.js (fetch wrapper + React hooks)
    ↓
router.py (FastAPI endpoints)
    ↓
services/
    broadcast.py  → Orchestration (CRUD, audience, dispatch)
    meta_api.py   → Meta WhatsApp Cloud API calls
    webhook.py    → Inbound webhook processing
    analytics.py  → Metrics aggregation
    ↓
database.py (SQLAlchemy async → MySQL)
    ↓
config.py (all external dependencies)
```

**Data flow for sending a broadcast:**
1. Merchant creates campaign in wizard UI → `POST /api/broadcasts` (saves draft)
2. Merchant clicks "Schedule Broadcast" → `POST /api/broadcasts/{id}/send`
3. `broadcast.py` resolves audience → queries contacts/segments from MySQL
4. `broadcast.py` dispatches messages concurrently via `meta_api.py`
5. Each message hits Meta's API → returns a `wamid` (message ID)
6. Results stored in `broadcast_recipients` table
7. Meta sends delivery/read webhooks → `webhook.py` updates recipient statuses
8. Merchant views analytics → `analytics.py` aggregates from recipient records

---

## File Map

```
broadcasts-backend/
├── config.py                    # All placeholders — fill this in first
├── database.py                  # SQLAlchemy async engine + table definitions
├── migrations.sql               # Run this to create MySQL tables
├── models.py                    # Pydantic schemas (request/response contracts)
├── router.py                    # FastAPI route definitions (14 endpoints)
├── services/
│   ├── analytics.py             # Metrics, funnel, list stats, cost calc
│   ├── broadcast.py             # Core orchestration (the biggest file)
│   ├── meta_api.py              # Meta Cloud API integration
│   └── webhook.py               # Webhook signature verify + status updates
└── frontend/
    └── api-client.js            # React service layer + hooks
```

---

## Setup Instructions

### Step 1: Install Python Dependencies

Add to your `requirements.txt`:

```
fastapi>=0.104
uvicorn[standard]>=0.24
pydantic>=2.0
pydantic-settings>=2.0
sqlalchemy[asyncio]>=2.0
aiomysql>=0.2.0
httpx>=0.25
```

### Step 2: Create MySQL Tables

Run `migrations.sql` against your AeroChat database:

```bash
mysql -u <user> -p <database> < migrations.sql
```

This creates 3 new tables:
- `broadcasts` — Campaign records
- `broadcast_recipients` — Per-recipient delivery tracking
- `csv_uploads` — Parsed CSV file storage

**It does NOT modify your existing tables.** But it expects your `contacts` table to have these columns:
- `id`, `name`, `phone`, `whatsapp_opted_in`, `country_code`

If `whatsapp_opted_in` or `country_code` don't exist, the migration file includes optional `ALTER TABLE` statements at the bottom — uncomment and run them.

### Step 3: Fill in config.py

Open `config.py` and replace every `PLACEHOLDER_*` value:

| Variable | Where to get it |
|----------|----------------|
| `META_ACCESS_TOKEN` | Meta Business Manager → System Users → Generate Token (needs `whatsapp_business_messaging` permission) |
| `META_PHONE_NUMBER_ID` | Meta Business Manager → WhatsApp → Phone Numbers |
| `META_WABA_ID` | Meta Business Manager → WhatsApp → Business Account |
| `META_WEBHOOK_VERIFY_TOKEN` | You define this string. Enter the same value in Meta's webhook setup. |
| `META_APP_SECRET` | Meta App Dashboard → Settings → Basic → App Secret |
| `DATABASE_URL` | Your MySQL connection string: `mysql+aiomysql://user:pass@host:3306/aerochat` |
| `AEROCHAT_API_BASE_URL` | Your internal API base URL |
| `AEROCHAT_INTERNAL_API_KEY` | Your service-to-service auth key |

All config values can also be set via environment variables with a `BROADCASTS_` prefix:
```bash
export BROADCASTS_META_ACCESS_TOKEN="your_token_here"
export BROADCASTS_DATABASE_URL="mysql+aiomysql://..."
```

Or via a `.env` file in your project root.

### Step 4: Mount the Router in Your FastAPI App

```python
# In your main FastAPI application file:

from fastapi import FastAPI
from broadcasts.router import router as broadcasts_router
from broadcasts.database import init_db, close_db

app = FastAPI()

# Mount the broadcasts module
app.include_router(broadcasts_router, prefix="/api/broadcasts", tags=["Broadcasts"])

@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()
```

### Step 5: Set Up Meta Webhooks

1. Go to Meta App Dashboard → WhatsApp → Configuration → Webhooks
2. Set the callback URL to: `https://your-domain.com/
`
3. Set the verify token to match `META_WEBHOOK_VERIFY_TOKEN` in your config
4. Subscribe to these webhook fields: `messages` (this covers both status updates and inbound messages)

### Step 6: Connect the Frontend

In your React admin app:

```javascript
// Install: copy frontend/api-client.js to your frontend source

import { broadcastsApi, useBroadcasts, useTemplates } from './api-client';

// In BroadcastsList component:
const { data, loading, error, refetch } = useBroadcasts({ status: 'sent', page: 1 });

// In BroadcastWizard component:
const { data: templateData } = useTemplates();
const result = await broadcastsApi.createBroadcast({ campaignName: '...', ... });
await broadcastsApi.sendBroadcast(result.id);
```

If your API lives on a different domain/port than your frontend, set:
```bash
REACT_APP_BROADCASTS_API_BASE=https://api.aerochat.com/api/broadcasts
```

### Step 7: Connect the Conversation Forwarder

The one remaining placeholder is in `webhook.py` → `_forward_to_conversation_handler()`. This forwards inbound WhatsApp messages to AeroChat's existing conversation system.

Your options:
1. **Direct function call** — if broadcasts runs in the same process as your conversation handler
2. **Internal API call** — `POST /api/conversations/inbound` (example code is in the file)
3. **Message queue** — push to Redis/RabbitMQ (recommended for production decoupling)

---

## API Endpoints Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/broadcasts/templates` | Fetch approved Meta templates (cached) |
| `GET` | `/api/broadcasts/segments` | List audience segments + opted-in count |
| `POST` | `/api/broadcasts/csv-upload` | Upload + parse CSV phone list |
| `GET` | `/api/broadcasts` | List broadcasts (filterable, paginated) |
| `GET` | `/api/broadcasts/stats` | Aggregate stats for list header |
| `POST` | `/api/broadcasts` | Create broadcast (draft) |
| `GET` | `/api/broadcasts/{id}` | Full detail + analytics |
| `PUT` | `/api/broadcasts/{id}` | Update draft/scheduled broadcast |
| `DELETE` | `/api/broadcasts/{id}` | Delete draft |
| `POST` | `/api/broadcasts/{id}/send` | Send now or schedule |
| `POST` | `/api/broadcasts/{id}/cancel` | Cancel scheduled broadcast |
| `POST` | `/api/broadcasts/{id}/duplicate` | Copy as new draft |
| `GET` | `/api/broadcasts/{id}/cost-estimate` | Estimate Meta messaging cost |
| `GET/POST` | `/api/broadcasts/webhook` | Meta webhook verify + receive |

Once running, visit `https://your-domain.com/docs` for auto-generated Swagger UI with request/response schemas.

---

## Existing Table Requirements

The module queries these tables that should already exist in your AeroChat database:

### contacts
| Column | Type | Required by |
|--------|------|-------------|
| `id` | VARCHAR(36) | Audience resolution |
| `name` | VARCHAR(200) | Template variable {{1}} |
| `phone` | VARCHAR(20) | Message delivery |
| `whatsapp_opted_in` | TINYINT(1) | Audience filtering |
| `country_code` | VARCHAR(5) | Cost calculation |

### segments
| Column | Type | Required by |
|--------|------|-------------|
| `id` | VARCHAR(36) | Segment audience selection |
| `name` | VARCHAR(200) | Audience label display |
| `description` | TEXT | Segment list display |

### segment_members
| Column | Type | Required by |
|--------|------|-------------|
| `segment_id` | VARCHAR(36) | Segment audience resolution |
| `contact_id` | VARCHAR(36) | Joining contacts to segments |

If your tables use different column names, update the raw SQL queries in `broadcast.py` and `analytics.py`. Search for the table name constants at the top of `broadcast.py`:

```python
CONTACTS_TABLE = settings.TABLE_CONTACTS        # default: "contacts"
SEGMENTS_TABLE = settings.TABLE_SEGMENTS         # default: "segments"
SEGMENT_MEMBERS_TABLE = settings.TABLE_SEGMENT_MEMBERS  # default: "segment_members"
```

---

## Key Design Decisions

**Async throughout.** Every database call and HTTP request is async. The dispatch loop uses `asyncio.Semaphore` to send up to 50 messages concurrently (configurable) without overwhelming Meta's rate limits.

**Forward-only status progression.** Webhook status updates only move forward: pending → sent → delivered → read → replied. A "delivered" webhook won't overwrite a "read" status. Failed is a terminal override. This is enforced by `status_is_advancement()` in `database.py`.

**Cumulative analytics counting.** A "read" message is also counted as "delivered" and "sent" in analytics. This matches how merchants think about funnel metrics — delivery rate should include all messages that eventually got delivered, not just those stuck at "delivered" status.

**Reply attribution window.** Inbound messages are matched to broadcasts within a configurable time window (default: 48 hours). If someone replies 3 days after receiving a broadcast, it won't count as a broadcast reply.

**CSV contacts are verified against opted-in status.** Phones in a CSV that match existing contacts are checked for `whatsapp_opted_in`. Phones not in the contacts table are assumed opted-in (the merchant is responsible for compliance).

**Template caching.** Templates are fetched from Meta once, then cached in memory for 5 minutes (configurable). This avoids hitting Meta's API on every wizard page load.

---

## Rate Limiting & Dispatch Tuning

These values in `config.py` control dispatch behavior:

| Setting | Default | What it does |
|---------|---------|-------------|
| `DISPATCH_CONCURRENCY` | 50 | Max simultaneous Meta API calls |
| `DISPATCH_BATCH_DELAY` | 1.0s | Pause between batches |
| `DISPATCH_MAX_RETRIES` | 3 | Retry failed sends |
| `DISPATCH_RETRY_DELAY` | 2.0s | Base delay for exponential backoff |
| `DISPATCH_TIMEOUT` | 30s | Per-message API timeout |

Meta's standard throughput is ~80 msgs/sec. The default of 50 concurrent leaves headroom. For high-throughput tier accounts, increase `DISPATCH_CONCURRENCY` to 80-100.

Non-retryable Meta error codes (invalid number, blocked, etc.) are detected and skipped immediately without wasting retry attempts.

---

## Testing

To test locally without sending real messages:

1. Set `META_ACCESS_TOKEN` to a test token from Meta's test environment
2. Use Meta's test phone number (available in the WhatsApp Cloud API dashboard)
3. Or mock `MetaAPIService.send_template_message()` to return fake results

For webhook testing, use Meta's webhook test tool in the App Dashboard, or tools like ngrok to expose your local server.

---

## Production Checklist

- [ ] `config.py` values filled in (no PLACEHOLDER_ remaining)
- [ ] `migrations.sql` executed against production MySQL
- [ ] Existing `contacts` table has `whatsapp_opted_in` and `country_code` columns
- [ ] FastAPI router mounted with `/api/broadcasts` prefix
- [ ] Meta webhook URL configured and verified
- [ ] `_forward_to_conversation_handler` connected to AeroChat conversations
- [ ] HTTPS enabled (Meta requires HTTPS for webhooks)
- [ ] Monitoring/alerting on dispatch failures and webhook errors
- [ ] Cost rates populated in `COST_RATES_BY_COUNTRY` for your target markets
- [ ] Backup strategy for `broadcast_recipients` table (grows fast)
