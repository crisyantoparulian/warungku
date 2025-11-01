"""
Vercel serverless function entry point
"""

from app.main import app

# Vercel will use the FastAPI app directly
handler = app