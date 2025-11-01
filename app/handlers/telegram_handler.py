import os
import asyncio
from typing import Dict, Any
from fastapi import Request
from ..models.database import TelegramMessage
from ..services.llm_service import LLMService


class TelegramHandler:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.admin_user_ids = self._get_admin_user_ids()
        self.llm_service = LLMService()

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")

    def _get_admin_user_ids(self) -> list:
        """Get list of admin user IDs from environment"""
        admin_ids = os.getenv("TELEGRAM_ADMIN_USER_IDS", "")
        if admin_ids:
            return [int(user_id.strip()) for user_id in admin_ids.split(",")]
        return []

    def _is_admin_user(self, user_id: int) -> bool:
        """Check if user is authorized admin"""
        if not self.admin_user_ids:
            # If no admin IDs are configured, allow all users (development mode)
            return True
        return user_id in self.admin_user_ids

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """Handle incoming Telegram webhook"""
        try:
            data = await request.json()

            # Check if it's a message
            if "message" not in data:
                return {"status": "ok"}

            message_data = data["message"]
            telegram_message = self._parse_telegram_message(message_data)

            # Check authorization
            if not self._is_admin_user(telegram_message.from_id):
                await self._send_message(
                    telegram_message.chat_id,
                    "Maaf, Anda tidak diizinkan menggunakan bot ini."
                )
                return {"status": "unauthorized"}

            # Process the message
            response_text = await self.llm_service.process_message(
                telegram_message.text,
                str(telegram_message.from_id)
            )

            # Send response back to Telegram
            await self._send_message(telegram_message.chat_id, response_text)

            return {"status": "success"}

        except Exception as e:
            print(f"Error handling webhook: {e}")
            return {"status": "error", "message": str(e)}

    def _parse_telegram_message(self, message_data: Dict[str, Any]) -> TelegramMessage:
        """Parse incoming Telegram message"""
        return TelegramMessage(
            message_id=message_data.get("message_id", 0),
            from_id=message_data["from"]["id"],
            chat_id=message_data["chat"]["id"],
            text=message_data.get("text", ""),
            date=message_data.get("date", 0)
        )

    async def _send_message(self, chat_id: int, text: str) -> None:
        """Send message to Telegram chat"""
        import httpx

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
        except Exception as e:
            print(f"Error sending message to Telegram: {e}")

    async def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook for Telegram bot"""
        import httpx

        url = f"https://api.telegram.org/bot{self.bot_token}/setWebhook"

        payload = {
            "url": webhook_url
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                result = response.json()
                return result.get("ok", False)
        except Exception as e:
            print(f"Error setting webhook: {e}")
            return False

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        import httpx

        url = f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error getting webhook info: {e}")
            return {"ok": False, "error": str(e)}