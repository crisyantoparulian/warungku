import os
from typing import List, Optional
from pydantic import BaseSettings


class Settings(BaseSettings):
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_USER_IDS: str = ""  # Comma-separated user IDs

    # LLM Configuration (GLM)
    GLM_API_KEY: str
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"

    # FastAPI Configuration
    APP_SECRET_KEY: str = "your-secret-key-here"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Webhook Configuration
    WEBHOOK_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def admin_user_ids(self) -> List[int]:
        """Parse admin user IDs from comma-separated string"""
        if not self.TELEGRAM_ADMIN_USER_IDS:
            return []
        return [int(user_id.strip()) for user_id in self.TELEGRAM_ADMIN_USER_IDS.split(",") if user_id.strip()]

    def is_admin_user(self, user_id: int) -> bool:
        """Check if user is in admin list"""
        if not self.admin_user_ids:
            # If no admin IDs are configured, allow all users (development mode)
            return True
        return user_id in self.admin_user_ids


# Global settings instance
settings = Settings()