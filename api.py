"""
Vercel serverless function entry point for FastAPI
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the FastAPI app
from app.main import app

# Vercel serverless function handler
handler = app

# For local development with Vercel CLI
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(handler, host="0.0.0.0", port=port)