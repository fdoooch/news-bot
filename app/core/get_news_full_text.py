import feedparser
import time
from newspaper import Article

def get_full_article_text(url):
    """
    Extract full text content from a news article URL
    """
    try:
        # Initialize article object
        article = Article(url)
        
        # Download and parse article
        article.download()
        article.parse()
        text = _clean_text(article.text)
        
        result = {
            'text': text,
            'title': article.title,
        }
        if article.has_top_image():
            result['top_image'] = article.top_image
        return result
    except Exception as e:
        print(f"Error extracting article content from {url}: {str(e)}")
        return None
    

def _clean_text(text: str) -> str:
    """
    Clean the text by removing unnecessary characters and blocks
    """
    text = text.replace("Decrypt’s Art, Fashion, and Entertainment Hub. Discover SCENE", "")
    text = text.split("Edited by")[0]
    text = text.strip()
    return text



def get_latest_news_with_content(feed_urls, target_categories):
    """
    Get the latest news with full content for each category
    """
    news_by_category = {}
    
    for feed_url in feed_urls:
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                # Get categories
                entry_categories = []
                if hasattr(entry, 'tags'):
                    entry_categories = [tag.term.lower() for tag in entry.tags]
                
                # Get image URL
                image_url = None
                if hasattr(entry, 'enclosures') and entry.enclosures:
                    for enclosure in entry.enclosures:
                        if enclosure.type and enclosure.type.startswith('image/'):
                            image_url = enclosure.url
                elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0]['url']
                
                # Check categories
                for category in target_categories:
                    if category.lower() in entry_categories:
                        # Get full article content
                        article_content = get_full_article_text(entry.link)
                        # article_content = get_full_article_text("https://decrypt.co/296539/chill-guy-solana-meme-coin-plummets-creator-hack")
                        
                        if article_content:
                            news_item = {
                                'title': entry.title,
                                'link': entry.link,
                                'published': entry.published,
                                'source': feed.feed.title,
                                'image_url': article_content['top_image'] or image_url,
                                'full_text': article_content['text'],
                                'timestamp': time.mktime(entry.published_parsed) if entry.get('published_parsed') else time.time()
                            }
                            
                            # Update if it's newer than existing entry
                            if category not in news_by_category or \
                               news_item['timestamp'] > news_by_category[category]['timestamp']:
                                news_by_category[category] = news_item
                
        except Exception as e:
            print(f"Error processing feed {feed_url}: {str(e)}")
    
    return news_by_category

def display_full_news(news_dict):
    """Display the latest news with full content for each category"""
    if not news_dict:
        print("No news found matching the criteria.")
        return
        
    for category, item in news_dict.items():
        print(f"\n{'='*20} {category.upper()} {'='*20}")
        print(f"Source: {item['source']}")
        print(f"Title: {item['title']}")
        print(f"Published: {item['published']}")
        print(f"Link: {item['link']}")
        if item['image_url']:
            print(f"Image: {item['image_url']}")
        print("\nFull Text:")
        print("-" * 50)
        print(item['full_text'])
        print("=" * 50)

# Example usage
if __name__ == "__main__":
    feeds = [
        "https://decrypt.co/feed",
    ]
    
    categories = [
        "Coins",
    ]
    
    # Get latest news with full content
    latest_news = get_latest_news_with_content(feeds, categories)
    
    # Display results
    display_full_news(latest_news)