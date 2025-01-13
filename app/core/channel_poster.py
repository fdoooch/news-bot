from aiogram import Bot, Dispatcher
from aiogram.types import FSInputFile
import asyncio
import re
import logging
from app.core.config import settings

logger = logging.getLogger(settings.LOGGER_NAME)

def _remove_html_tags(text):
    return re.sub(r'<[^>]+>', '', text)

def _extract_title_from_rewrited_news(text: str) -> str:
    title = text.split('\n')[0]
    title = _remove_html_tags(title)
    return title

class ChannelPoster:
    def __init__(self, token: str, target_channels_ids: list[str], service_channels_ids: list[str]):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.target_channels_ids = target_channels_ids
        self.service_channels_ids = service_channels_ids


    async def publish_news(self, message: str, image_path: str = None):
        if not self.target_channels_ids:
            logger.warning("No channels specified for publishing news.")
            return
        title = _extract_title_from_rewrited_news(message)
        logger.info(f"Publishing news: {title} to channels: {', '.join(self.target_channels_ids)}")

        for channel_id in self.target_channels_ids:            
            await self.send_photo(chat_id=f"@{channel_id}", image_path=image_path, caption=message, parse_mode="HTML")
        for channel_id in self.service_channels_ids:            
            await self.send_photo(chat_id=f"@{channel_id}", image_path=image_path, caption=message, parse_mode="HTML")
        


    async def send_service_report(self, channels_ids: list[str], message: str):
        if not self.service_channels_ids:
            logger.warning("No channels specified for sending service report.")
            return
        title = _extract_title_from_rewrited_news(message)
        logger.info(f"Sending service report {title} to channels: {', '.join(channels_ids)}")

        for channel_id in self.service_channels_ids:
            await self.send_text(chat_id=f"@{channel_id}", text=message, parse_mode="HTML")
    

    async def send_text(self, chat_id: str, text: str, parse_mode: str = None) -> bool:
        """Send text message to channel"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logging.error(f"Error sending text message: {e}")
            raise
    
    async def send_photo(self, chat_id: str, image_path: str, caption: str = None, parse_mode: str = None) -> bool:
        """Send photo to channel"""
        try:
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(image_path),
                caption=caption,
                parse_mode=parse_mode,
            )
            return True
        except Exception as e:
            logging.error(f"Error sending photo: {e}")
            raise
    
    async def close(self):
        """Close bot session"""
        await self.bot.session.close()

async def main():
    # Bot configuration
    BOT_TOKEN = "your_bot_token_here"
    CHANNEL_ID = "@your_channel_name"
    poster = ChannelPoster(BOT_TOKEN, CHANNEL_ID)
    
    try:
        # Send simple text
        await poster.send_text("Hello, channel!")
        
        # Send formatted text
        html_message = """
        <b>Important Announcement!</b>
        
        This is a <i>formatted</i> message with:
        • <code>Special formatting</code>
        • <a href='https://example.com'>Links</a>
        • And more!
        """
        await poster.send_text(html_message, parse_mode="HTML")
        
        # Send photo with caption
        await poster.send_photo(
            "path/to/your/photo.jpg",
            caption="Check out this awesome photo!"
        )
        
        # Send document
        await poster.send_document(
            "path/to/your/document.pdf",
            caption="Important document"
        )
        
    finally:
        await poster.close()

if __name__ == '__main__':
    asyncio.run(main())