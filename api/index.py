import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=== API INDEX.PY STARTING ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.executable}")

try:
    logger.info("Attempting to import main.app...")
    from main import app
    logger.info("Successfully imported main.app")
except Exception as e:
    logger.error(f"FAILED TO IMPORT MAIN: {type(e).__name__}: {e}", exc_info=True)
    raise

logger.info("=== API INDEX.PY READY ===")

