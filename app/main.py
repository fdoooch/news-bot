from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import json
from datetime import datetime as dt
import logging
from app.core.config import settings
from app.core.parse_news_feed import get_latest_news_by_categories
from app.core.get_news_full_text import get_full_article_text
from app.core.news_rewriter import NewsRewriter
from app.core.download_image import temp_download_async
from app.core.channel_poster import ChannelPoster
from app.core.prepare_image import convert_and_resize_image

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


async def _publish_news_job():
    
    with open(os.path.join(settings.TMP_DIR, 'last_published.json'), 'r') as file:
        last_published = json.load(file)
    
    news_feed = get_latest_news_by_categories(settings.rss_feed.URLS, settings.rss_feed.CATEGORIES, last_published)
    for category, news_items in news_feed.items():
        if not news_items:
            logger.info(f"No fresh news found for category: {category}")
            continue
        for item in news_items:
            await _process_news_item(item)
            logger.info(f"Published {item['title']}:[{category}]")


def print_job_info(scheduler):
    # Get all jobs
    jobs = scheduler.get_jobs()
    
    logger.info("\nScheduled Jobs:")
    logger.info("-" * 50)
    for job in jobs:
        logger.info(f"Job ID: {job.id}")
        logger.info(f"Next run time: {job.next_run_time}")
        logger.info(f"Trigger: {job.trigger}")
        logger.info(f"Function: {job.func.__name__}")
        logger.info("-" * 50)



async def _process_news_item(item: dict):
    full_text = get_full_article_text(item.get('link')).get('text')
    image_url = item.get('img')
    title = item.get('title')
    news_rewriter = NewsRewriter(settings.openai.API_KEY)
    rewrited_text = news_rewriter.rewrite_text(full_text)
    title = news_rewriter.write_title(title)
    poster = ChannelPoster(settings.tg_bot.TOKEN, settings.tg_bot.TARGET_CHANNELS)
    await _publish_news_to_tg_channels(poster, rewrited_text, title=title, image_url=image_url)



async def _publish_news_to_tg_channels(poster: ChannelPoster, message: str, title: str, image_url: str = None):
    try:
        async with temp_download_async(image_url, prefix=f"{settings.TMP_DIR}/downloading_") as temp_path:
            prepared_image_path = convert_and_resize_image(temp_path, f"{temp_path}_prepared")
            await poster.publish_news(message, title, image_path=prepared_image_path)
        
    finally:
        await poster.close()

    



if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
