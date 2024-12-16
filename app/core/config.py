from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
)
import os
import logging


BASE_DIR = Path(__file__).resolve().parent.parent

env_filepath = os.path.join(BASE_DIR.parent, ".env")
# print(f"ENV: {env_filepath}")
if os.path.exists(env_filepath):
    from dotenv import load_dotenv

    load_dotenv(env_filepath)
else:
    print(f"No .env file found at {env_filepath}")


class TgBotSettings(BaseModel):
    TOKEN: str = os.getenv("TG_BOT_API_TOKEN")
    TARGET_CHANNELS: list[str] = Field(
        default_factory=lambda: (
            os.getenv("TG_BOT_TARGET_CHANNELS", "").split(",")
            if os.getenv("TG_BOT_TARGET_CHANNELS")
            else []
        )
    )

class RssFeedSettings(BaseModel):
    URLS: list[str] = Field(
        default_factory=lambda: (
            os.getenv("RSS_FEED_URLS", "").split(",")
            if os.getenv("RSS_FEED_URLS")
            else []
        )
    )
    CATEGORIES: list[str] = Field(
        default_factory=lambda: (
            os.getenv("RSS_CATEGORIES", "").split(",")
            if os.getenv("RSS_CATEGORIES")
            else []
        )
    )

class OpenAISettings(BaseModel):
    API_KEY: str = os.getenv("OPENAI_API_KEY")
    MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo") #gpt-3.5-turbo, gpt-4o-mini
    TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", 0.7))
    MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", 500))
    PROJECT_ID: str = os.getenv("OPENAI_PROJECT_ID", "news-publisher")

class Settings(BaseSettings):
    PROJECT_NAME: str = "News Publisher"
    PROJECT_DESCRIPTION: str = "Parse news from RSS feeds and send them to Telegram groups"
    openai: OpenAISettings = OpenAISettings()
    tg_bot: TgBotSettings = TgBotSettings()
    rss_feed: RssFeedSettings = RssFeedSettings()
    LOGGER_NAME: str = "news_publisher"
    BASE_DIR: str = str(BASE_DIR)
    TMP_DIR: str = os.path.join(Path(BASE_DIR).resolve(), "tmp")


settings = Settings()

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname).3s | %(name)s -> %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
fmt = logging.Formatter(
    fmt="%(asctime)s %(levelname).3s | %(name)s -> %(funcName)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(settings.LOGGER_NAME)
for handler in logger.handlers:
    handler.setFormatter(fmt)
logger.setLevel(logging.DEBUG)