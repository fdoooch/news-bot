from app.core.config import settings
from app.core.parse_news_feed import get_latest_news_by_categories
from app.core.get_news_full_text import get_full_article_text
from app.core.news_rewriter import NewsRewriter
from app.core.download_image import temp_download_async
from app.core.channel_poster import ChannelPoster

async def main():
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

    # full_text = get_full_article_text(news_feed[settings.rss_feed.CATEGORIES[0]][0].get('link')).get('text')
    # image_url = news_feed[settings.rss_feed.CATEGORIES[0]][0].get('img')
    # title = news_feed[settings.rss_feed.CATEGORIES[0]][0].get('title')
    # news_rewriter = NewsRewriter(settings.openai.API_KEY)
    # rewrited_text = news_rewriter.rewrite_text(full_text)
    # title = news_rewriter.write_title(title)
    # poster = ChannelPoster(settings.tg_bot.TOKEN, settings.tg_bot.TARGET_CHANNELS)
    # await _publish_news_to_tg_channels(poster, rewrited_text, title=title, image_url=image_url)


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
        print(f"Image url: {image_url}")
        async with temp_download_async(image_url, prefix=f"{settings.TMP_DIR}/downloading_") as temp_path:
            print(f"Temp path: {temp_path}")
            await poster.publish_news(message, title, image_path=str(temp_path))

        # await poster.publish_news(message, image_url=image_url)
        # await poster.publish_news(message, image_url=None)
        
        # # Send photo with caption
        # await poster.send_photo(
        #     "path/to/your/photo.jpg",
        #     caption="Check out this awesome photo!"
        # )
        
        # # Send document
        # await poster.send_document(
        #     "path/to/your/document.pdf",
        #     caption="Important document"
        # )
        
    finally:
        await poster.close()

    



if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
