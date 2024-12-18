import feedparser
from datetime import datetime
from dateutil import parser
from collections import defaultdict

def get_latest_news_by_categories(feed_urls: list[str], target_categories: list[str]) -> dict:
    """
    Get the latest news for each specified category
    
    Args:
        feed_urls (list): List of RSS feed URLs
        target_categories (list): List of categories to filter
    
    Returns:
        dict: Latest news items grouped by category
    """
    news_by_category = defaultdict(list)
    
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                # Get entry categories (converted to lowercase)
                entry_categories = []
                if hasattr(entry, 'tags'):
                    entry_categories = [tag.term.lower() for tag in entry.tags]

                # Parse the publication date
                try:
                    pub_date = parser.parse(entry.published)
                    if not _is_today(pub_date):
                        continue
                except (AttributeError, ValueError):
                    # If parsing fails, try alternative date fields or skip
                    try:
                        pub_date = parser.parse(entry.published, datetime.now().isoformat())
                    except (AttributeError, ValueError):
                        pub_date = datetime.now()  # Use current time as fallback
                
                # Check if entry matches any of our target categories
                for category in target_categories:
                    if category.lower() in entry_categories:
                        news_item = {
                            'title': entry.title,
                            'link': entry.link,
                            'published_at': pub_date,
                            'source': feed.feed.title,
                            'summary': entry.get('summary', '')[:200] + '...',
                        }
                        if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                            news_item['img'] = entry.media_thumbnail[0]['url']
                        news_by_category[category].append(news_item)
                        
            # Sort each category's news by publication date and keep only the latest
            result = {}
            for category in news_by_category:
                result[category] = sorted(news_by_category[category], key=lambda x: x['published_at'], reverse=True)[:1]
                
        except Exception as e:
            print(f"Error processing feed {feed_url}: {str(e)}")
    return dict(result)


def display_latest_news(news_dict: dict):
    """Display the latest news for each category"""
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
            print(f"Image: {item['img']}")
        print('='*50)


def _is_today(date):
    today = datetime.now()
    return date.date() == today.date()


# Example usage
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
    
    # Get the latest news for each category
    latest_news = get_latest_news_by_categories(feeds, categories)
    
    # Display the results
    display_latest_news(latest_news)