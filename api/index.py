from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Minimal FastAPI app - no complex imports
app = FastAPI(title="WhatsApp Broadcast API")

logger.info("FastAPI app created successfully")

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "API is running on Vercel"}

@app.get("/api/broadcasts/webhook")
async def verify_webhook(request: Request):
    """Webhook verification endpoint"""
    try:
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        logger.info(f"Webhook verification: mode={mode}, token={token}, challenge={challenge}")
        
        # Match the token from environment or hardcoded for now
        VERIFY_TOKEN = "890@passwordMetawhatsapp"
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return JSONResponse(content=int(challenge), status_code=200)
        
        logger.warning(f"Webhook verification failed")
        return JSONResponse(content={"error": "Verification failed"}, status_code=403)
    except Exception as e:
        logger.error(f"Error in webhook verification: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/broadcasts/webhook")
async def receive_webhook(request: Request):
    """Receive webhook events"""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error receiving webhook: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

logger.info("All routes registered successfully")


