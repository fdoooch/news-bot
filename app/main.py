from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from pathlib import Path
import json
from datetime import datetime as dt
import logging
from app.core.config import settings
from app.core.exceptions import RewritedNewsIsTooLongError
from app.core.sources.decrypt_co.parse_news_feed import get_latest_news_by_categories
from app.core.get_news_full_text import get_full_article_text
from app.core.news_rewriter import NewsRewriter
from app.core.download_image import temp_download_async
from app.core.channel_poster import ChannelPoster
from app.core.prepare_image import convert_and_resize_image
from app.core.sources.beincrypto_com.parse_news_feed import FeedRader as BeincryptoFeedRader
from app.core.sources.decrypt_co.parse_news_feed import FeedReader as DecryptFeedRader

logger = logging.getLogger(settings.LOGGER_NAME)

async def main():
    print("Hello from news-bot!")
    if not os.path.exists(settings.TMP_DIR):
            os.makedirs(settings.TMP_DIR)

    # create last_published.json if it doesn't exist
    if not os.path.exists(os.path.join(settings.TMP_DIR, 'last_published.json')):
        with open(os.path.join(settings.TMP_DIR, 'last_published.json'), 'w') as file:
            json.dump({}, file)

    # Create the scheduler
    scheduler = AsyncIOScheduler()
    for item in settings.PUBLISHING_SCHEDULE.split(','):
        hours, minutes = item.split(':')
        scheduler.add_job(
            _publish_news_job,
            CronTrigger(hour=hours, minute=minutes),  # 24-hour format
        )

    scheduler.start()
    print_job_info(scheduler)
    
    try:
        # Keep the main program running
        pause_lenght = 15
        while True:
            if dt.now().minute == 0 and dt.now().second < pause_lenght:
                logger.info(f"Runnung. Next post at {scheduler.get_jobs()[0].next_run_time}")
            await asyncio.sleep(pause_lenght)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


async def _publish_news_job(source: str, category: str):
    
    with open(os.path.join(settings.TMP_DIR, 'last_published.json'), 'r') as file:
        last_published = json.load(file)

    last_published_at = last_published.get(source, {}).get(category, None)

    if source == "beincrypto_com":
        source_reader = BeincryptoFeedRader()
        feed_url ="https://beincrypto.com/press-release/feed/"
    elif source == "decrypt_co":
        source_reader = DecryptFeedRader()
        feed_url = "https://decrypt.co/feed"
    else:
        logger.error(f"Unknown source: {source}")
        await _send_service_report(f"Unknown source: {source}")
        return
    
    news_feed = source_reader.get_latest_news_by_category(
        feed_url=feed_url,
        target_category=category,
        prev_published=last_published_at,
        max_news_count=1,
        tmp_dir=Path(settings.TMP_DIR)
    )
    if len(news_feed) == 0:
        logger.info("No fresh news found.")
        await _send_service_report("No fresh news found.")
        return
    


    
    for category, news_items in news_feed.items():
        if not news_items:
            logger.info(f"No fresh news found for category: {category}")
            await _send_service_report(f"No fresh news found for category: {category}")
            continue
        for item in news_items:
            try:
                await _process_news_item(item)
                logger.info(f"Published {item['title']}:[{category}]")
                _update_published_dates(last_published, category, item['published_at'], settings.TMP_DIR)
                
            except RewritedNewsIsTooLongError as e:
                await _send_service_report(f"Error. Rewrited news is too long ({e.rewrited_news_length}):\n{str(e.rewrited_news)}")
                return
            except Exception as e:
                logger.error(f"Error publishing news: {str(e)}")
                await _send_service_report(f"Error publishing news: {str(e)}")
            

def _update_published_dates(prev_published: dict[str, dt], category: str, pub_date: dt, tmp_dir: Path) -> None:
    """Update and persist published dates."""
    prev_published[category.lower()] = pub_date.isoformat()
    
    try:
        with (tmp_dir / 'last_published.json').open('w') as file:
            json.dump(prev_published, file)
    except IOError as e:
        logger.error(f"Failed to update published dates: {e}")



def print_job_info(scheduler):
    # Get all jobs
    jobs = scheduler.get_jobs()
    
    logger.info("Scheduled Jobs:")
    logger.info("-" * 50)
    for job in jobs:
        logger.info(f"Publishing news from: {settings.rss_feed.URLS}")
        logger.info(f"Publishing news to channels: {', '.join(settings.tg_bot.TARGET_CHANNELS)}")
        logger.info(f"Next run time: {job.next_run_time}")
        logger.info(f"Function: {job.func.__name__}")
        logger.info("-" * 50)


async def _process_news_item(item: dict):
    full_text = get_full_article_text(item.get('link')).get('text')
    image_url = item.get('img')
    title = item.get('title')
    news_rewriter = NewsRewriter(settings.openai.API_KEY)
    news = news_rewriter.rewrite_news(
        news_text=full_text,
        news_title=title,
        max_news_text_len=settings.NEWS_TEXT_MAX_LENGTH,
        max_rewriting_tries=settings.MAX_REWRITING_TRIES
    )

    poster = ChannelPoster(settings.tg_bot.TOKEN, settings.tg_bot.TARGET_CHANNELS, settings.tg_bot.SERVICE_CHANNELS)
    await _publish_news_to_tg_channels(poster, news, image_url=image_url)
    

async def _send_service_report(msg: str):
    poster = ChannelPoster(settings.tg_bot.TOKEN, settings.tg_bot.TARGET_CHANNELS, settings.tg_bot.SERVICE_CHANNELS)

    await poster.send_service_report(settings.tg_bot.SERVICE_CHANNELS, msg)


async def _publish_news_to_tg_channels(poster: ChannelPoster, message: str, image_url: str = None):
    try:
        async with temp_download_async(image_url, prefix=f"{settings.TMP_DIR}/downloading_") as temp_path:
            prepared_image_path = convert_and_resize_image(temp_path, f"{temp_path}_prepared")
            await poster.publish_news(message, image_path=prepared_image_path)
        
    finally:
        await poster.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
