from pathlib import Path
from typing import List
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import logging
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
from urllib.parse import urlparse

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parent.parent

@lru_cache()
def load_env_file() -> bool:
    """Load environment variables from .env file."""
    env_file = find_dotenv(str(BASE_DIR / ".env"))
    if env_file:
        return load_dotenv(env_file)
    print(f"No .env file found in {BASE_DIR}")
    return False

# Load environment variables
load_env_file()

class TgBotSettings(BaseModel):
    """Telegram Bot configuration settings."""
    TOKEN: str = Field(
        default=os.getenv("TG_BOT_API_TOKEN"),
        description="Telegram Bot API Token"
    )
    TARGET_CHANNELS: list[str] = Field(
        default_factory=lambda: (
            os.getenv("TG_BOT_TARGET_CHANNELS", "").split(",")
            if os.getenv("TG_BOT_TARGET_CHANNELS")
            else []
        ),
        description="List of target Telegram channels"
    )

    @property
    def has_valid_config(self) -> bool:
        """Check if Telegram configuration is valid."""
        return bool(self.TOKEN and self.TARGET_CHANNELS)

    @field_validator('TARGET_CHANNELS')
    @classmethod
    def validate_channels(cls, v):
        """Validate and clean channel list."""
        validated_channels = []
        for channel in v:
            channel = channel.strip()
            if channel:
                if not channel.startswith('@'):
                    channel = f'@{channel}'
                validated_channels.append(channel)
        return validated_channels

class RssFeedSettings(BaseModel):
    """RSS Feed configuration settings."""
    URLS: list[str] = Field(
        default_factory=lambda: (
            os.getenv("RSS_FEED_URLS", "").split(",")
            if os.getenv("RSS_FEED_URLS")
            else []
        ),
        description="List of RSS feed URLs"
    )
    CATEGORIES: list[str] = Field(
        default_factory=lambda: (
            os.getenv("RSS_CATEGORIES", "").split(",")
            if os.getenv("RSS_CATEGORIES")
            else []
        ),
        description="List of RSS categories to filter"
    )

    @field_validator('URLS')
    @classmethod
    def validate_urls(cls, v):
        """Validate and clean URLs."""
        validated_urls = []
        for url in v:
            url = url.strip()
            if url:
                try:
                    result = urlparse(url)
                    if all([result.scheme, result.netloc]):
                        validated_urls.append(url)
                    else:
                        raise ValueError(f"Invalid URL format: {url}")
                except Exception:
                    raise ValueError(f"Invalid URL: {url}")
        return validated_urls

    @field_validator('CATEGORIES')
    @classmethod
    def validate_categories(cls, v):
        """Validate and clean categories."""
        return [cat.strip() for cat in v if cat.strip()]

class OpenAISettings(BaseModel):
    """OpenAI configuration settings."""
    API_KEY: str = Field(
        default=os.getenv("OPENAI_API_KEY"),
        description="OpenAI API Key"
    )
    MODEL: str = Field(
        default=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        description="OpenAI Model name"
    )
    TEMPERATURE: float = Field(
        default=float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        ge=0.0,
        le=1.0,
        description="OpenAI temperature parameter"
    )
    MAX_TOKENS: int = Field(
        default=int(os.getenv("OPENAI_MAX_TOKENS", "500")),
        gt=0,
        description="Maximum tokens for OpenAI response"
    )
    PROJECT_ID: str = Field(
        default=os.getenv("OPENAI_PROJECT_ID", "news-publisher"),
        description="Project identifier"
    )

    @field_validator('TEMPERATURE', mode='before')
    @classmethod
    def validate_temperature(cls, v):
        """Validate and convert temperature."""
        try:
            temp = float(v)
            if not 0 <= temp <= 1:
                raise ValueError("Temperature must be between 0 and 1")
            return temp
        except (TypeError, ValueError):
            raise ValueError("Temperature must be a valid number between 0 and 1")

    @field_validator('MAX_TOKENS', mode='before')
    @classmethod
    def validate_max_tokens(cls, v):
        """Validate and convert max tokens."""
        try:
            tokens = int(v)
            if tokens <= 0:
                raise ValueError("MAX_TOKENS must be positive")
            return tokens
        except (TypeError, ValueError):
            raise ValueError("MAX_TOKENS must be a valid positive integer")

class Settings(BaseSettings):
    """Main application settings."""
    PROJECT_NAME: str = "News Publisher"
    PROJECT_DESCRIPTION: str = "Parse news from RSS feeds and send them to Telegram groups"
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    tg_bot: TgBotSettings = Field(default_factory=TgBotSettings)
    rss_feed: RssFeedSettings = Field(default_factory=RssFeedSettings)
    LOGGER_NAME: str = "news_publisher"
    APP_DIR: Path = Field(default_factory=lambda: APP_DIR)
    TMP_DIR: Path = Field(default_factory=lambda: APP_DIR / "tmp")
    LOGS_DIR: Path = Field(default_factory=lambda: BASE_DIR / "logs")
    PUBLISHING_SCHEDULE: str = Field(
        default="17:25",
        description="Schedule for publishing news in HH:MM format (24-hour)"
    )
    
    model_config = SettingsConfigDict(case_sensitive=True)

    @field_validator("PUBLISHING_SCHEDULE")
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        """Validate schedule string."""
        return v

    @model_validator(mode='after')
    def validate_schedule_times(self):
        """Validate all schedule times after model creation."""
        schedule = self.PUBLISHING_SCHEDULE.split(',')
        validated_times = []
        
        for time in schedule:
            time = time.strip()
            try:
                parsed_time = datetime.strptime(time, "%H:%M").time()
                validated_times.append(f"{parsed_time.hour:02d}:{parsed_time.minute:02d}")
            except ValueError:
                raise ValueError(f"Invalid time format: {time}. Use HH:MM format (24-hour)")
        
        self.PUBLISHING_SCHEDULE = ','.join(validated_times)
        return self

    @property
    def publishing_schedule_list(self) -> List[str]:
        """Get publishing schedule as a list."""
        return [time.strip() for time in self.PUBLISHING_SCHEDULE.split(',')]

    @property
    def is_valid(self) -> bool:
        """Check if all required configurations are valid."""
        return all([
            self.openai.API_KEY,
            self.tg_bot.has_valid_config,
            self.rss_feed.URLS
        ])

    def check_paths(self) -> bool:
        """Check if all required paths are writable."""
        try:
            test_file = self.TMP_DIR / '.write_test'
            test_file.touch()
            test_file.unlink()
            return True
        except (OSError, IOError) as e:
            logger.error(f"Path check failed: {str(e)}")
            return False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ensure_tmp_dir()
        if not self.check_paths():
            logger.warning("Some paths are not writable. Check permissions.")

    def ensure_tmp_dir(self):
        """Ensure temporary directory exists."""
        self.TMP_DIR.mkdir(parents=True, exist_ok=True)

def setup_logging(settings: Settings) -> logging.Logger:
    """Configure and setup logging."""
    # Get logger instance
    logger = logging.getLogger(settings.LOGGER_NAME)
    
    # Set logger level
    logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname).3s | %(name)s -> %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Prevent propagation to root logger to avoid double logging
    logger.propagate = False
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler
    log_file = settings.LOGS_DIR / "out.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

# Initialize settings
settings = Settings()

# Setup logging
logger = setup_logging(settings)

# Validate settings on import
if not settings.is_valid:
    logger.warning("Invalid configuration detected. Please check your environment variables.")