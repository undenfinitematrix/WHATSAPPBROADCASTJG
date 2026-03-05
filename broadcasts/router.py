"""
AeroChat Broadcasts Module — API Router
=========================================
FastAPI route definitions for all broadcast endpoints.
Mount this router in your main FastAPI app:

    from broadcasts.router import router as broadcasts_router
    app.include_router(broadcasts_router, prefix="/api/broadcasts", tags=["Broadcasts"])
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Request, Depends
from fastapi.responses import JSONResponse

from .config import settings
from .models import (
    BroadcastCreate,
    BroadcastUpdate,
    BroadcastListResponse,
    BroadcastDetail,
    BroadcastStats,
    BroadcastSummary,
    BroadcastStatus,
    BroadcastDispatchResult,
    CostEstimate,
    TemplateListResponse,
    SegmentListResponse,
    CSVUploadResult,
    SuccessResponse,
    ErrorResponse,
)
from .services.meta_api import MetaAPIService
from .services.broadcast import BroadcastService
from .services.webhook import WebhookService
from .services.analytics import AnalyticsService

logger = logging.getLogger("broadcasts")

router = APIRouter()


# =========================================
# Dependency injection
# =========================================
# In production, replace these with your actual database session
# and service initialization pattern.

async def get_meta_service() -> MetaAPIService:
    return MetaAPIService()

async def get_broadcast_service() -> BroadcastService:
    return BroadcastService()

async def get_webhook_service() -> WebhookService:
    return WebhookService()

async def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


# =========================================
# Templates
# =========================================

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    meta: MetaAPIService = Depends(get_meta_service),
):
    """
    Fetch approved WhatsApp templates from Meta API.
    Results are cached for TEMPLATE_CACHE_TTL seconds.
    """
    try:
        templates = await meta.get_approved_templates()
        return TemplateListResponse(
            templates=templates,
            cached=meta.last_fetch_was_cached,
            cached_at=meta.cache_timestamp,
        )
    except Exception as e:
        logger.error(f"Failed to fetch templates: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch templates from Meta: {str(e)}")


# =========================================
# Segments / Audience
# =========================================

@router.get("/segments", response_model=SegmentListResponse)
async def list_segments(
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    List available audience segments and total opted-in count.
    """
    try:
        segments = await broadcast_svc.get_segments()
        total_opted_in = await broadcast_svc.get_total_opted_in_count()
        return SegmentListResponse(segments=segments, total_opted_in=total_opted_in)
    except Exception as e:
        logger.error(f"Failed to fetch segments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# CSV Upload
# =========================================

@router.post("/csv-upload", response_model=CSVUploadResult)
async def upload_csv(
    file: UploadFile = File(...),
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Upload and parse a CSV file of phone numbers.
    Validates format, deduplicates, returns valid phone list.
    """
    # Validate file size
    content = await file.read()
    if len(content) > settings.CSV_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.CSV_MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    try:
        result = await broadcast_svc.parse_csv_upload(content, file.filename)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"CSV upload failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process CSV file")


# =========================================
# Broadcast CRUD
# =========================================

@router.get("", response_model=BroadcastListResponse)
async def list_broadcasts(
    status: Optional[BroadcastStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    List broadcasts with optional filtering by status and search.
    Supports pagination.
    """
    try:
        result = await broadcast_svc.list_broadcasts(
            status=status,
            search=search,
            page=page,
            page_size=page_size,
        )
        return result
    except Exception as e:
        logger.error(f"Failed to list broadcasts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=BroadcastStats)
async def get_broadcast_stats(
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """
    Get aggregate stats for the broadcasts list page header.
    Compares current month to previous month.
    """
    try:
        return await analytics.get_list_stats()
    except Exception as e:
        logger.error(f"Failed to get broadcast stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=BroadcastSummary, status_code=201)
async def create_broadcast(
    data: BroadcastCreate,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Create a new broadcast (saved as draft).
    """
    # log the validated payload so we know what the client actually sent
    # use INFO level so it shows up with default logging configuration
    logger.info(f"create_broadcast payload: {data.dict()}")
    try:
        broadcast = await broadcast_svc.create_broadcast(data)
        return broadcast
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create broadcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{broadcast_id}", response_model=BroadcastDetail)
async def get_broadcast(
    broadcast_id: str,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """
    Get full broadcast detail including analytics.
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    # Enrich with analytics if sent
    if broadcast.status == BroadcastStatus.SENT:
        analytics_data = await analytics.get_broadcast_analytics(broadcast_id)
        broadcast.metrics = analytics_data.metrics
        broadcast.funnel = analytics_data.funnel
        broadcast.sent_count = analytics_data.sent_count
        broadcast.delivered_count = analytics_data.delivered_count
        broadcast.read_count = analytics_data.read_count
        broadcast.replied_count = analytics_data.replied_count
        broadcast.failed_count = analytics_data.failed_count

    return broadcast


@router.put("/{broadcast_id}", response_model=BroadcastSummary)
async def update_broadcast(
    broadcast_id: str,
    data: BroadcastUpdate,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Update a draft or scheduled broadcast.
    Cannot update sent/sending broadcasts.
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    if broadcast.status not in (BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot update broadcast with status '{broadcast.status}'"
        )

    try:
        updated = await broadcast_svc.update_broadcast(broadcast_id, data)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update broadcast {broadcast_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{broadcast_id}", response_model=SuccessResponse)
async def delete_broadcast(
    broadcast_id: str,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Delete a draft broadcast. Cannot delete sent/sending/scheduled broadcasts.
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    if broadcast.status != BroadcastStatus.DRAFT:
        raise HTTPException(
            status_code=409,
            detail=f"Can only delete drafts. This broadcast is '{broadcast.status}'"
        )

    await broadcast_svc.delete_broadcast(broadcast_id)
    return SuccessResponse(message="Broadcast deleted")


# =========================================
# Broadcast Actions
# =========================================

@router.post("/{broadcast_id}/send", response_model=BroadcastDispatchResult)
async def send_broadcast(
    broadcast_id: str,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Send or schedule a broadcast.
    - If schedule_type is 'now': dispatches immediately.
    - If schedule_type is 'schedule': marks as scheduled (scheduler picks it up).
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    if broadcast.status not in (BroadcastStatus.DRAFT, BroadcastStatus.SCHEDULED):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot send broadcast with status '{broadcast.status}'"
        )

    if not broadcast.template_name:
        raise HTTPException(status_code=422, detail="No template selected")

    try:
        result = await broadcast_svc.send_broadcast(broadcast_id)
        return result
    except Exception as e:
        logger.error(f"Failed to send broadcast {broadcast_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Dispatch failed: {str(e)}")


@router.post("/{broadcast_id}/cancel", response_model=SuccessResponse)
async def cancel_broadcast(
    broadcast_id: str,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Cancel a scheduled broadcast. Cannot cancel sent/sending broadcasts.
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    if broadcast.status != BroadcastStatus.SCHEDULED:
        raise HTTPException(
            status_code=409,
            detail=f"Can only cancel scheduled broadcasts. This is '{broadcast.status}'"
        )

    await broadcast_svc.cancel_broadcast(broadcast_id)
    return SuccessResponse(message="Broadcast cancelled")


@router.post("/{broadcast_id}/duplicate", response_model=BroadcastSummary, status_code=201)
async def duplicate_broadcast(
    broadcast_id: str,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Duplicate a broadcast as a new draft.
    Copies template, audience, and settings but not analytics.
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    try:
        new_broadcast = await broadcast_svc.duplicate_broadcast(broadcast_id)
        return new_broadcast
    except Exception as e:
        logger.error(f"Failed to duplicate broadcast {broadcast_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# Cost Estimation
# =========================================

@router.get("/{broadcast_id}/cost-estimate", response_model=CostEstimate)
async def get_cost_estimate(
    broadcast_id: str,
    broadcast_svc: BroadcastService = Depends(get_broadcast_service),
):
    """
    Estimate the Meta messaging cost for a broadcast.
    Based on recipient count and per-country rates.
    """
    broadcast = await broadcast_svc.get_broadcast(broadcast_id)
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")

    try:
        estimate = await broadcast_svc.estimate_cost(broadcast_id)
        return estimate
    except Exception as e:
        logger.error(f"Failed to estimate cost for {broadcast_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# Webhooks (Meta calls these)
# =========================================

@router.get("/webhook", response_model=None)
async def verify_webhook(
    request: Request,
):
    """
    Meta webhook verification (GET).
    Meta sends hub.mode, hub.verify_token, hub.challenge.
    We echo back hub.challenge if the token matches.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    # Compare against token configured in settings so it can be changed
    # without touching code. Meta must be configured with the same value.
    if mode == "subscribe" and token == settings.META_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return JSONResponse(content=int(challenge), status_code=200)

    logger.warning(f"Webhook verification failed: mode={mode}, token={token}")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    webhook_svc: WebhookService = Depends(get_webhook_service),
):
    """
    Meta webhook receiver (POST).
    Processes delivery status updates and inbound messages.
    Always returns 200 quickly — processing happens async.
    """
    body = await request.body()

    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not webhook_svc.verify_signature(body, signature):
        logger.warning("Webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse and queue for processing (don't block the response)
    payload = await request.json()
    try:
        await webhook_svc.process_webhook(payload)
    except Exception as e:
        # Log but don't fail — Meta will retry if we return non-200
        logger.error(f"Webhook processing error: {e}")

    # Always return 200 to Meta
    return {"status": "ok"}
