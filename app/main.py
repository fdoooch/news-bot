import os
import json
import datetime as dt
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
from app.core.config import settings
from app.core.exceptions import RewritedNewsIsTooLongError
from app.core.news_rewriter import NewsRewriter
from app.core.download_image import temp_download_async
from app.core.channel_poster import ChannelPoster
from app.core.prepare_image import convert_and_resize_image
from app.core.sources.beincrypto_com.parse_news_feed import FeedReader as BeincryptoFeedRader
from app.core.sources.decrypt_co.parse_news_feed import FeedReader as DecryptFeedRader
from app.core.scheduler import SchedulerManager
from app.core.models import NewsItem

logger = logging.getLogger(settings.LOGGER_NAME)

# Global configurations
SOURCE_READERS = {
    "beincrypto_com": {
        "reader": BeincryptoFeedRader(),
        "feed_url": "https://beincrypto.com/press-release/feed/"
    },
    "decrypt_co": {
        "reader": DecryptFeedRader(),
        "feed_url": "https://decrypt.co/feed"
    }
}

async def send_service_report(msg: str):
    """Send service report to designated channels."""
    poster = ChannelPoster(
        settings.tg_bot.TOKEN,
        settings.tg_bot.TARGET_CHANNELS,
        settings.tg_bot.SERVICE_CHANNELS
    )
    try:
        await poster.send_service_report(settings.tg_bot.SERVICE_CHANNELS, msg)
    except Exception as e:
        logger.error(f"Failed to send service report: {str(e)}")
    finally:
        await poster.close()

async def publish_news_to_channels(message: str, image_url: str = None):
    """Publish news to telegram channels."""
    poster = ChannelPoster(
        settings.tg_bot.TOKEN,
        settings.tg_bot.TARGET_CHANNELS,
        settings.tg_bot.SERVICE_CHANNELS
    )
    try:
        if image_url:
            async with temp_download_async(image_url, prefix=f"{settings.TMP_DIR}/downloading_") as temp_path:
                prepared_image_path = convert_and_resize_image(temp_path, f"{temp_path}_prepared")
                await poster.publish_news(message, image_path=prepared_image_path)
        else:
            await poster.publish_news(message)
    finally:
        await poster.close()

def update_published_dates(prev_published: dict, source: str, category: str, pub_date: dt.datetime) -> None:
    """Update and persist published dates."""
    try:
        source = source.lower()
        category = category.lower()
        
        if source not in prev_published:
            prev_published[source] = {}
        
        prev_published[source][category] = pub_date.isoformat()
        
        last_published_file = Path(settings.TMP_DIR) / 'last_published.json'
        last_published_file.write_text(json.dumps(prev_published))
        
    except Exception as e:
        logger.error(f"Failed to update published dates: {str(e)}")

def load_last_published() -> Dict[str, Any]:
    """Load last published dates from JSON file."""
    try:
        last_published_file = Path(settings.TMP_DIR) / 'last_published.json'
        return json.loads(last_published_file.read_text())
    except Exception as e:
        logger.error(f"Error reading last published dates: {str(e)}")
        return {}

async def process_and_publish_item(item: NewsItem, source: str, category: str, prev_published: dict):
    """Process and publish a single news item."""
    try:
        news_rewriter = NewsRewriter(settings.openai.API_KEY)
        news = news_rewriter.rewrite_news(
            news_url=item.link,
            max_news_text_len=settings.NEWS_TEXT_MAX_LENGTH,
            max_rewriting_tries=settings.MAX_REWRITING_TRIES
        )
        
        await publish_news_to_channels(news, item.img_link)
        
        update_published_dates(
            prev_published, source, category, item.published_at
        )
        
        logger.info(f"Published {item.title} [{source} -> {category}]")
        await send_service_report(f"Published {item.title} [{source} -> {category}]\n{item.link}")
        
    except RewritedNewsIsTooLongError as e:
        await send_service_report(
            f"Error. Rewritten news is too long ({e.rewrited_news_length}):\n{str(e.rewrited_news)}"
        )
    except Exception as e:
        logger.error(f"Error processing news item: {str(e)}")
        raise

async def publish_news_job(**kwargs):
    """Execute the news publishing job."""
    source = kwargs.get('source')
    category = kwargs.get('category')
    
    try:
        prev_published = load_last_published()
        last_published_at_str = prev_published.get(source, {}).get(category)
        last_published_at = dt.datetime.strptime(last_published_at_str, "%Y-%m-%dT%H:%M:%S%z") if last_published_at_str else None
        
        source_config = SOURCE_READERS.get(source)
        if not source_config:
            raise ValueError(f"Unknown source: {source}")
        
        news_feed = source_config["reader"].get_latest_news_by_category(
            feed_url=source_config["feed_url"],
            target_category=category,
            prev_published=last_published_at,
            max_news_count=1,
            tmp_dir=Path(settings.TMP_DIR)
        )
        
        if not news_feed:
            await send_service_report(
                f"No fresh news found for category: {category} at {source}"
            )
            return
        
        for item in news_feed:
            await process_and_publish_item(item, source, category, prev_published)
            
    except Exception as e:
        error_msg = f"Error in publish job ({source}/{category}): {str(e)}"
        logger.error(error_msg)
        await send_service_report(error_msg)

async def run_publisher():
    """Run the news publisher."""
    print("Starting News Publisher...")
    
    # Initialize
    os.makedirs(settings.TMP_DIR, exist_ok=True)
    last_published_file = Path(settings.TMP_DIR) / 'last_published.json'
    if not last_published_file.exists():
        last_published_file.write_text('{}')
    
    # Set up scheduler
    scheduler = SchedulerManager()
    scheduler.remove_all_jobs()
    # Schedule jobs
    for item in settings.PUBLISHING_SCHEDULE:
        for time_str in item['time']:
            try:
                hours, minutes = map(int, time_str.split(':'))
                job_id = f"publish_news_{item['source']}_{item['category']}_{hours}_{minutes}"
                
                scheduler.schedule_job(
                    job_func=publish_news_job,
                    job_id=job_id,
                    hours=hours,
                    minutes=minutes,
                    source=item['source'],
                    category=item['category']
                )
            except ValueError as e:
                logger.error(f"Invalid time format in schedule: {time_str} - {str(e)}")
            except Exception as e:
                logger.error(f"Failed to schedule job: {str(e)}")
    
    scheduler.start()
    print(scheduler.get_jobs_report())
    
    try:
        while True:
            period = 15
            if dt.datetime.now().minute == 0 and dt.datetime.now().second < period:
                next_job = scheduler.scheduler.get_jobs()[0].next_run_time
                logger.info(f"Running. Next post scheduled for {next_job}")
            await asyncio.sleep(period)
            
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        scheduler.shutdown(wait=True)

async def main():
    await run_publisher()

if __name__ == "__main__":
    asyncio.run(main())