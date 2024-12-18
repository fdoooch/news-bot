from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
from app.core.config import settings
from app.core.parse_news_feed import get_latest_news_by_categories
from app.core.get_news_full_text import get_full_article_text
from app.core.news_rewriter import NewsRewriter
from app.core.download_image import temp_download_async
from app.core.channel_poster import ChannelPoster
from app.core.prepare_image import convert_and_resize_image

async def main():

    if not os.path.exists(settings.TMP_DIR):
            os.makedirs(settings.TMP_DIR)
    # Create the scheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule the task to run at 2:30 PM every day
    scheduler.add_job(
        _publish_news_job,
        CronTrigger(hour=settings.PUBLISHING_SCHEDULE_HOURS, minute=settings.PUBLISHING_SCHEDULE_MINUTES),  # 24-hour format
    )
    
    scheduler.start()
    
    try:
        # Keep the main program running
        while True:
            await asyncio.sleep(15)
            print_job_info(scheduler)
    except (KeyboardInterrupt, SystemExit):
        # Shut down scheduler gracefully
        scheduler.shutdown()


async def _publish_news_job():
    print("Hello from news-bot!")
    news_feed = get_latest_news_by_categories(settings.rss_feed.URLS, settings.rss_feed.CATEGORIES)
    for category, news_items in news_feed.items():
        print(f"\n{'='*20} {category.upper()} {'='*20}")
        for item in news_items:
            print(f"Title: {item['title']}")
            print(f"Published: {item['published_at']}")
            print(f"Image: {item['img']}")
            await _process_news_item(item)
        print('='*50)


def print_job_info(scheduler):
    # Get all jobs
    jobs = scheduler.get_jobs()
    
    print("\nScheduled Jobs:")
    print("-" * 50)
    for job in jobs:
        print(f"Job ID: {job.id}")
        print(f"Next run time: {job.next_run_time}")
        print(f"Trigger: {job.trigger}")
        print(f"Function: {job.func.__name__}")
        print("-" * 50)



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
