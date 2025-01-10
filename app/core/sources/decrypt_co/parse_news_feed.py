import logging
import datetime as dt
from datetime import timezone, timedelta
from pathlib import Path

import feedparser
from dateutil import parser

from app.core.config import settings
from app.core.models import NewsItem

logger = logging.getLogger(__name__)


class FeedReader:

    def get_latest_news_by_category(
        self,
        feed_url: str,
        target_category: str | None = None,
        max_news_count: int = 1,
        prev_published: dt.datetime | None = None,
        tmp_dir: Path = None
    ) -> list[NewsItem]:
        """
        Get the latest news for each specified category.
        
        Args:
            feed_urls: List of RSS feed URLs
            target_categories: List of categories to filter
            prev_published: Dictionary of previously published dates by category
            tmp_dir: Path to temporary directory for storing state
        
        Returns:
            List of latest news items sorted by publication date
        """
        prev_published = prev_published or {}
        tmp_dir = tmp_dir or Path(settings.TMP_DIR)
        
        category_news: list[NewsItem] = []
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo:  # Check if feed parsing had errors
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
                return category_news
                
            for entry in feed.entries:
                pub_date = _parse_publication_date(entry)

                if _is_too_old(pub_date, prev_published, timedelta_days=1):
                    continue

                if target_category:
                    entry_categories = _extract_categories(entry)
                    if target_category.lower() not in entry_categories:
                        continue

                # if _is_already_published(pub_date, prev_published, target_category):
                #     logger.info(f"Skipping already published news item: {entry.link}")
                #     continue
                    
                news_item = create_news_item(entry, feed, pub_date, target_category)
                category_news.append(news_item)
                    
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")
        
        # Sort and limit results
        return sorted(category_news, key=lambda x: x.published_at, reverse=True)[:max_news_count]

def _parse_publication_date(entry: feedparser.FeedParserDict) -> dt.datetime | None:
    """
    Parse publication date from feed entry with fallback options.
    Returns timezone-aware datetime or None if too old.
    """
    date_fields = ['published', 'updated', 'created']
    
    for field in date_fields:
        try:
            if hasattr(entry, field):
                # Parse date and ensure it's timezone-aware
                date = parser.parse(getattr(entry, field))
                
                # If date is naive, assume UTC
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                return date
        except (AttributeError, ValueError):
            continue
    
    # Return current time in UTC
    return dt.now(timezone.utc)


def _is_too_old(pub_date: dt.datetime, prev_published: dt.datetime, timedelta_days: int=1) -> bool:
    """
    Check if the publication date is older than 1 day.
    Ensures timezone-aware comparison.
    """
    threshold = dt.datetime.now(timezone.utc) - timedelta(days=timedelta_days)
    if pub_date < threshold:
        return True
    result = pub_date <= prev_published if prev_published else False
    return result

# def _is_already_published(published: dt.datetime, prev_published: dict[str, dt.datetime], categories: list[str]) -> bool:
#     """
#     Check if the publication date is older than the previously published date.
#     Ensures timezone-aware comparison.
#     """
#     if not prev_published:
#         return False
#     for category in categories:
#         if not prev_published.get(category.lower()):
#             continue
#         if prev_published.get(category.lower()) >= published.isoformat():
#             return True
#     return False


def _extract_categories(entry: feedparser.FeedParserDict) -> list[str]:
    """Extract categories from feed entry."""
    if hasattr(entry, 'tags'):
        return [tag.term.lower() for tag in entry.tags]
    return []

def create_news_item(entry: feedparser.FeedParserDict, feed: feedparser.FeedParserDict, pub_date: dt.datetime, category: str | None) -> NewsItem:
    """Create a structured news item from feed entry."""
    news_item = NewsItem(
        title=entry.title,
        link=entry.link,
        published_at=pub_date,
        source=feed.feed.title,
        category=category,
        summary=entry.get('summary', '')[:200] + '...',
        img_link=None
    )

    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        news_item.img_link = entry.media_thumbnail[0]['url']
    
    return news_item



def display_latest_news(news_list: list[NewsItem]) -> None:
    """Display the latest news for each category."""
    for item in news_list:
        print(f"\nSource: {item.source}")
        print(f"Title: {item.title}")
        print(f"Published: {item.published_at}")
        print(f"Category: {item.category}")
        print(f"Link: {item.link}")
        print(f"Summary: {item.summary}")
        print(f"Image: {item.img_link or 'No image available'}")
        print('='*50)

if __name__ == "__main__":
    # List of RSS feeds to check
    feed = "https://decrypt.co/feed"
        # "https://beincrypto.com/press-release/feed"
    
    
    # List of categories you're interested in
    categories = [
        "Coins",
        "Gaming",

    ]

    # prev_published = {"gaming": "2024-12-18T17:01:02+00:00", "coins": "2024-12-18T16:00:58+00:00"}
    prev_published = dt.datetime.strptime("2024-12-18T17:01:02+00:00", "%Y-%m-%dT%H:%M:%S%z")
    # prev_published = None
    
    # Get the latest news for each category
    feed_reader = FeedReader()
    latest_news = feed_reader.get_latest_news_by_category(
        feed_url=feed,
        target_category="Gaming",
        prev_published=prev_published,
        tmp_dir=Path(settings.TMP_DIR)
    )
    
    # Display the results
    display_latest_news(latest_news)