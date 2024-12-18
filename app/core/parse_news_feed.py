import json
import logging
from collections import defaultdict
from datetime import datetime as dt, timezone
from datetime import timedelta
from pathlib import Path
from typing import TypedDict

import feedparser
from dateutil import parser

from app.core.config import settings

logger = logging.getLogger(__name__)

class NewsItem(TypedDict):
    title: str
    link: str
    published_at: dt
    source: str
    summary: str
    img: str | None


def get_latest_news_by_categories(
    feed_urls: list[str],
    target_categories: list[str],
    prev_published: dict[str, dt] = None,
    tmp_dir: Path = None
) -> dict[str, list[NewsItem]]:
    """
    Get the latest news for each specified category.
    
    Args:
        feed_urls: List of RSS feed URLs
        target_categories: List of categories to filter
        prev_published: Dictionary of previously published dates by category
        tmp_dir: Path to temporary directory for storing state
    
    Returns:
        Dictionary of latest news items grouped by category
    """
    prev_published = prev_published or {}
    tmp_dir = tmp_dir or Path(settings.TMP_DIR)
    
    news_by_category: dict[str, list[NewsItem]] = defaultdict(list)
    target_categories_lower = {cat.lower() for cat in target_categories}
    
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo:  # Check if feed parsing had errors
                logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")
                continue
                
            for entry in feed.entries:
                pub_date = _parse_publication_date(entry)

                if _is_too_old(pub_date):
                    continue
                    
                entry_categories = extract_categories(entry)
                
                matching_categories = target_categories_lower.intersection(entry_categories)
                if not matching_categories:
                    continue

                if _is_already_published(pub_date, prev_published, matching_categories):
                    logger.info(f"Skipping already published news item: {entry.link}")
                    continue
                    
                news_item = create_news_item(entry, feed, pub_date)
                
                for category in matching_categories:
                    news_by_category[category].append(news_item)
                    _update_published_dates(prev_published, category, pub_date, tmp_dir)
                    
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")
            continue
    
    # Sort and limit results
    return {
        category: sorted(items, key=lambda x: x['published_at'], reverse=True)[:1]
        for category, items in news_by_category.items()
    }

def _parse_publication_date(entry: feedparser.FeedParserDict) -> dt | None:
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

def _is_too_old(published: dt) -> bool:
    """
    Check if the publication date is older than 1 day.
    Ensures timezone-aware comparison.
    """
    threshold = dt.now(timezone.utc) - timedelta(days=1)
    return published < threshold

def _is_already_published(published: dt, prev_published: dict[str, dt], categories: list[str]) -> bool:
    """
    Check if the publication date is older than the previously published date.
    Ensures timezone-aware comparison.
    """
    if not prev_published:
        return False
    for category in categories:
        if not prev_published.get(category.lower()):
            continue
        if prev_published.get(category.lower()) >= published.isoformat():
            return True
    return False


def extract_categories(entry: feedparser.FeedParserDict) -> list[str]:
    """Extract categories from feed entry."""
    if hasattr(entry, 'tags'):
        return [tag.term.lower() for tag in entry.tags]
    return []

def create_news_item(entry: feedparser.FeedParserDict, feed: feedparser.FeedParserDict, pub_date: dt) -> NewsItem:
    """Create a structured news item from feed entry."""
    news_item: NewsItem = {
        'title': entry.title,
        'link': entry.link,
        'published_at': pub_date,
        'source': feed.feed.title,
        'summary': entry.get('summary', '')[:200] + '...',
        'img': None
    }
    
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        news_item['img'] = entry.media_thumbnail[0]['url']
    
    return news_item

def _update_published_dates(prev_published: dict[str, dt], category: str, pub_date: dt, tmp_dir: Path) -> None:
    """Update and persist published dates."""
    prev_published[category.lower()] = pub_date.isoformat()
    
    try:
        with (tmp_dir / 'last_published.json').open('w') as file:
            json.dump(prev_published, file)
    except IOError as e:
        logger.error(f"Failed to update published dates: {e}")

def display_latest_news(news_dict: dict[str, list[NewsItem]]) -> None:
    """Display the latest news for each category."""
    for category, news_items in news_dict.items():
        print(f"\n{'='*20} {category.upper()} {'='*20}")
        if not news_items:
            print(f"No news found for category: {category}")
            continue
            
        for item in news_items:
            print(f"\nSource: {item['source']}")
            print(f"Title: {item['title']}")
            print(f"Published: {item['published_at']}")
            print(f"Link: {item['link']}")
            print(f"Summary: {item['summary']}")
            print(f"Image: {item.get('img', 'No image available')}")
        print('='*50)

if __name__ == "__main__":
    # List of RSS feeds to check
    feeds = [
        "https://decrypt.co/feed"
    ]
    
    # List of categories you're interested in
    categories = [
        "Coins",
        "Gaming",
    ]

    prev_published = {"gaming": "2024-12-18T17:01:02+00:00", "coins": "2024-12-18T16:00:58+00:00"}
    
    # Get the latest news for each category
    latest_news = get_latest_news_by_categories(
        feed_urls=feeds,
        target_categories=categories,
        prev_published=prev_published,
        tmp_dir=Path(settings.TMP_DIR)
    )
    
    # Display the results
    display_latest_news(latest_news)