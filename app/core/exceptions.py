class RewritedNewsIsTooLongError(Exception):
    
    def __init__(self, error_message: str, original_news: str = None, rewrited_news: str = None, rewrited_news_length: int = 0):
        self.message = f"Rewrited news is too long: {error_message}"
        self.original_news = original_news
        self.rewrited_news = rewrited_news
        self.rewrited_news_length = rewrited_news_length