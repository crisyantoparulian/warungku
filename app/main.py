from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from .handlers.telegram_handler import TelegramHandler
from .middleware.auth import APIKeyMiddleware, RateLimitMiddleware

# Load environment variables from .env file
load_dotenv()


# Initialize FastAPI app
app = FastAPI(
    title="WarungKu Bot API",
    description="Telegram bot for product management using LLM",
    version="1.0.0"
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Add CORS middleware (restrictive for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],  # Empty for production, add specific domains in development
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Restrict methods
    allow_headers=["*"],
)

# Add rate limiting (60 requests per minute per IP)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Add API key middleware (exclude public endpoints)
app.add_middleware(APIKeyMiddleware, exclude_paths=["/", "/health", "/test", "/webhook/telegram"])

# Initialize Telegram handler
telegram_handler = TelegramHandler()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "WarungKu Bot API is running",
        "status": "healthy"
    }


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook"""
    try:
        result = await telegram_handler.handle_webhook(request)
        return JSONResponse(content=result)
    except Exception as e:
        print(f"Webhook error: {e}")
        return JSONResponse(
            content={"status": "error", "message": "Internal server error"},
            status_code=500
        )


@app.get("/webhook/set")
async def set_webhook(webhook_url: str = None):
    """Set Telegram webhook (for setup purposes)"""
    try:
        # If no URL provided, use the ngrok URL or default
        if not webhook_url:
            webhook_url = os.getenv("WEBHOOK_URL", "")
            if not webhook_url:
                raise HTTPException(
                    status_code=400,
                    detail="webhook_url parameter is required"
                )

        success = await telegram_handler.set_webhook(webhook_url)

        if success:
            return {"status": "success", "webhook_url": webhook_url}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to set webhook"
            )
    except Exception as e:
        print(f"Set webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/webhook/info")
async def get_webhook_info():
    """Get current webhook information"""
    try:
        info = await telegram_handler.get_webhook_info()
        return JSONResponse(content=info)
    except Exception as e:
        print(f"Get webhook info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": os.getenv("DEBUG", "False")
    }


@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    return {
        "message": "Test endpoint is working",
        "environment_variables": {
            "SUPABASE_URL": "✓ Set" if os.getenv("SUPABASE_URL") else "✗ Missing",
            "TELEGRAM_BOT_TOKEN": "✓ Set" if os.getenv("TELEGRAM_BOT_TOKEN") else "✗ Missing",
            "GLM_API_KEY": "✓ Set" if os.getenv("GLM_API_KEY") else "✗ Missing",
            "ADMIN_USER_IDS": os.getenv("TELEGRAM_ADMIN_USER_IDS", "Not set")
        }
    }


# For development server
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting WarungKu Bot API on {host}:{port}")
    print("Available endpoints:")
    print("  GET  /              - Root")
    print("  POST /webhook/telegram - Telegram webhook")
    print("  GET  /webhook/set  - Set webhook")
    print("  GET  /webhook/info - Get webhook info")
    print("  GET  /health       - Health check")
    print("  GET  /test         - Test endpoint")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )