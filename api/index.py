from main import app

# Vercel Python runtime expects an ASGI app called "app".
# By importing the FastAPI `app` instance from the project root,
# all routes defined in `main.py` and included routers will be available.

# No additional code needed; Vercel will invoke this file for any
# /api/* request if routes in vercel.json redirect to it.
