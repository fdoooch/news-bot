from dataclasses import dataclass
import datetime as dt
from datetime import timezone, timedelta
from typing import List, Optional
import httpx
from httpx import HTTPError
import xml.etree.ElementTree as ET
from pathlib import Path
import logging

from app.core.config import settings
from app.core.models import NewsItem

logger = logging.getLogger(settings.LOGGER_NAME)

@dataclass
class FeedItem:
    """Data class to store RSS feed item information."""
    title: str
    link: str
    creator: Optional[str]
    pub_date: dt.datetime
    categories: List[str]
    description: str
    content: str
    media_url: Optional[str]
    guid: str

@dataclass
class FeedMetadata:
    """Data class to store RSS feed metadata."""
    title: str
    link: str
    description: str
    language: str
    last_build_date: dt.datetime
    image_url: Optional[str]

@dataclass
class Feed:
    """Data class to represent complete RSS feed."""
    metadata: FeedMetadata
    items: List[FeedItem]


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
        tmp_dir = tmp_dir or Path(settings.TMP_DIR)
        target_category = target_category.lower()
        
        category_news: list[NewsItem] = []
        try:
            feed = fetch_rss_feed(feed_url)

            for entry in feed.items:
                if _is_too_old(entry.pub_date, prev_published):
                    continue
                
                if target_category and target_category not in entry.categories:
                    continue
                
                news_item = _create_news_item(entry, target_category)
                category_news.append(news_item)
        except Exception as e:
            logger.error(f"Error processing feed {feed_url}: {str(e)}")

        # Sort and limit results
        return sorted(category_news, key=lambda x: x.published_at, reverse=True)[:max_news_count]


def fetch_rss_feed(url: str, timeout: float = 30.0) -> Optional[Feed]:
    """
    Fetch and parse RSS feed from URL using httpx.
    
    Args:
        url (str): URL of the RSS feed
        timeout (float): Request timeout in seconds
        
    Returns:
        Optional[Feed]: Parsed feed data or None if fetching/parsing fails
    """
    try:
        # Set up headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create httpx client with timeout
        timeout_config = httpx.Timeout(timeout)
        
        # Use context manager for proper resource cleanup
        with httpx.Client(timeout=timeout_config, follow_redirects=True) as client:
            # Fetch the feed
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            # Parse the feed
            return parse_rss_feed(response.text)
        
    except HTTPError as e:
        logger.error(f"Failed to fetch feed from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching feed from {url}: {e}")
        return None

def parse_date(date_str: str) -> dt.datetime:
    """Parse RSS date string to datetime object."""
    try:
        return dt.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    except ValueError as e:
        logger.error(f"Failed to parse date: {date_str}. Error: {e}")
        return dt.datetime.now()

def parse_rss_feed(xml_content: str) -> Optional[Feed]:
    """
    Parse RSS feed XML content and return structured data.
    
    Args:
        xml_content (str): Raw XML content of the RSS feed
        
    Returns:
        Optional[Feed]: Parsed feed data or None if parsing fails
    """
    try:
        # Parse XML
        root = ET.fromstring(xml_content)
        channel = root.find('channel')
        if channel is None:
            logger.error("No channel element found in RSS feed")
            return None

        # Parse feed metadata
        metadata = FeedMetadata(
            title=channel.findtext('title', ''),
            link=channel.findtext('link', ''),
            description=channel.findtext('description', ''),
            language=channel.findtext('language', 'en'),
            last_build_date=parse_date(channel.findtext('lastBuildDate', '')),
            image_url=channel.find('.//image/url').text if channel.find('.//image/url') is not None else None
        )

        # Parse items
        items = []
        for item_elem in channel.findall('item'):
            # Extract media URL
            media_content = item_elem.find('.//{http://search.yahoo.com/mrss/}content')
            media_url = media_content.get('url') if media_content is not None else None
            
            if not media_url:
                media_thumbnail = item_elem.find('.//{http://search.yahoo.com/mrss/}thumbnail')
                media_url = media_thumbnail.get('url') if media_thumbnail is not None else None

            # Extract categories
            categories = [cat.text.lower() for cat in item_elem.findall('category') if cat.text]

            # Create FeedItem
            item = FeedItem(
                title=item_elem.findtext('title', '').strip(),
                link=item_elem.findtext('link', '').strip(),
                creator=item_elem.findtext('.//{http://purl.org/dc/elements/1.1/}creator', '').strip(),
                pub_date=parse_date(item_elem.findtext('pubDate', '')),
                categories=categories,
                description=item_elem.findtext('description', '').strip(),
                content=item_elem.findtext('.//{http://purl.org/rss/1.0/modules/content/}encoded', '').strip(),
                media_url=media_url,
                guid=item_elem.findtext('guid', '').strip()
            )
            items.append(item)

        return Feed(metadata=metadata, items=items)

    except ET.ParseError as e:
        logger.error(f"Failed to parse XML: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while parsing feed: {e}")
        return None
    
def _is_too_old(pub_date: dt.datetime, prev_published: dt.datetime | None, timedelta_days: int=1) -> bool:
    """
    Check if the publication date is older than 1 day.
    Ensures timezone-aware comparison.
    """
    threshold = dt.datetime.now(timezone.utc) - timedelta(days=timedelta_days)
    if pub_date < threshold:
        return True
    return pub_date <= prev_published if prev_published else False


def _create_news_item(item: FeedItem, category: str) -> NewsItem:
    return NewsItem(
        title=item.title,
        link=item.link,
        published_at=item.pub_date,
        source=item.creator,
        category=category,
        summary=item.description,
        img_link=item.media_url
    )


def format_feed_item(item: NewsItem) -> str:
    """
    Format a feed item into a readable string.
    
    Args:
        item (FeedItem): Feed item to format
        
    Returns:
        str: Formatted string representation of the feed item
    """
    return f"""
Title: {item.title}
source: {item.source}
Published: {item.published_at}
Categories: {item.category}
Link: {item.link}
Media: {item.img_link or 'No media'}
"""



# Example usage:
if __name__ == "__main__":
    # URL of the RSS feed
    feed_url = "https://beincrypto.com/press-release/feed/"
    
    # # Fetch and parse feed
    # feed = fetch_rss_feed(feed_url)
    # if feed:
    #     print(f"Feed: {feed.metadata.title}")
    #     print(f"Last updated: {feed.metadata.last_build_date}")
    #     print("\nLatest items:")
    #     for item in feed.items[:3]:  # Show first 3 items
    #         print(format_feed_item(item))
    feed_reader = FeedReader()
    news = feed_reader.get_latest_news_by_category(
        feed_url=feed_url,
        target_category="Press Releases",
        max_news_count=3
    )

    for item in news:
        print(format_feed_item(item))

    # print("\n FULL TEXT:")
    # from app.core.news_rewriter import NewsRewriter
    
    # rewriter = NewsRewriter(api_key=settings.openai.API_KEY)
    # # url = feed.items[0].link
    # url = "https://beincrypto.com/swan-ico-set-to-launch-today"
    # # url = "https://decrypt.co/300398/bitcoin-93000-december-jobs-report-inflation"
    # print(rewriter.rewrite_news(url))