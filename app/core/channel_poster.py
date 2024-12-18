from aiogram import Bot, Dispatcher, html
from aiogram.types import FSInputFile
import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger(settings.LOGGER_NAME)

class ChannelPoster:
    def __init__(self, token: str, channels_ids: list[str]):
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        self.channels_ids = channels_ids


    async def publish_news(self, message: str, title: str = None, image_path: str = None):
        for channel_id in self.channels_ids:
            logger.info(f"Sending news to channel @{channel_id}")
#             bottom_text = f"""📱 {html.link("DC", "https://discord.gg/myvTswfa3s")}  | 📱 {html.link("TG", "https://t.me/questszone")}  | 📱 {html.link("CIS", "https://t.me/questszone_ru")}  | 📱 {html.link("YT", "https://www.youtube.com/@QuestsZone")}

# #quests_zone"""
            bottom_text = """
#quests_zone"""
            text = f"<b>{title.upper()}</b>\n\n{message}\n{bottom_text}"
            await self.send_photo(chat_id=f"@{channel_id}", image_path=image_path, caption=text, parse_mode="HTML")
    
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
            return False
    
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
            return False
    
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