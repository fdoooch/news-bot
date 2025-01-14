import openai
import re
import logging

from app.core.config import settings
from app.core.exceptions import RewritedNewsIsTooLongError

logger = logging.getLogger(settings.LOGGER_NAME)


class NewsRewriter:
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key"""
        self.client = openai.OpenAI(api_key=api_key, project=settings.openai.PROJECT_ID)


    def rewrite_news(self, news_url: str, max_news_text_len: int = 1000, max_rewriting_tries: int = 3):
        for _ in range(max_rewriting_tries):
            news =  self.rewrite_news_from_url(news_url)
            if len(news) <= max_news_text_len:
                return news
            logger.warning("Rewrited news is too long. Trying again...")
            logger.info(f"REWRITED TEXT: {news}")
        raise RewritedNewsIsTooLongError(
            error_message="Unable to rewrite news in setted length",
            original_news=f"from {news_url}",
            rewrited_news=news,
            rewrited_news_length=len(news)
        )

    def rewrite_news_from_url(self, url: str) -> str:
        prompt = create_rewriting_from_url_prompt(url)
        response = self.client.chat.completions.create(
            model=settings.openai.MODEL,
            messages=[
                {"role": "system", "content": "You are a professional content rewriter specializing in the 'Ghost on the block' style. STRICT OUTPUT LIMIT: 400 symbols."},
                {"role": "user", "content": prompt}
            ],
            temperature=settings.openai.TEMPERATURE,
            max_tokens=settings.openai.MAX_TOKENS
        )
        text = response.choices[0].message.content
        title = self.create_title(text)
        return format_news(news_text=text, news_title=title)
    
    def rewrite_text(self, text: str) -> str:
        """
        Rewrite text using ChatGPT
        
        Args:
            text: Original text to rewrite
            style: Optional style instruction
        """
        try:
            prompt = create_rewriting_prompt(text)
            
            response = self.client.chat.completions.create(
                model=settings.openai.MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional content rewriter specializing in the 'Ghost on the block' style. STRICT OUTPUT LIMIT: 400 symbols."},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.openai.TEMPERATURE,
                max_tokens=settings.openai.MAX_TOKENS
            )
            
            text = response.choices[0].message.content
            title = self.create_title(text)
            return format_news(news_text=text, news_title=title)
            
        except Exception as e:
            logger.error(f"Error in rewriting text: {str(e)}")
            return text  # Return original text if rewriting fails

    def create_title(self, text: str) -> str:
        try:
            prompt = create_title_prompt(text)
            
            response = self.client.chat.completions.create(
                model=settings.openai.MODEL,
                messages=[
                    {"role": "system", "content": "You are a professional caption creator specializing in the 'Ghost on the block' style. STRICT OUTPUT LIMIT: 77 symbols."},
                    {"role": "user", "content": prompt}
                ],
                temperature=settings.openai.TEMPERATURE,
                max_tokens=settings.openai.MAX_TOKENS
            )
            title = response.choices[0].message.content
            # remove " if its on the sides
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1]
            return title
            
        except Exception as e:
            print(f"Error in writing title: {str(e)}")
            return ""  # Return empty string if title writing fails



def create_rewriting_from_url_prompt(url: str) -> str:
    prompt = f"""
Make a concise rewrite of the article from {url} in the “Ghost on the block” style. Omit mentioning the source, focus only on the most important points. Keep non-source links from the text intact. Limit the rewrite to 600 characters. Use conversational American English.

Required:
 • Short sentences.
 • Friendly tone.
 • Include external links present in the original article (except for the source link).
 • Highlight key details and provide a call to action.
"""
    
    # prompt = f"Сделай краткий рерайт на английском языке данной статьи {url} в стиле ghost on the block без указания источника, только самые важные моменты, сохрани ссылки не на источник, до 1000 символов."
    return add_examples_to_the_prompt(prompt)


def create_rewriting_prompt(source_text):
    prompt = f"""
You are a professional content rewriter specializing in the "Ghost-on-the-block" style.
STRICT LIMIT: 400 symbols max!
IGNORE THIS LIMIT = FAIL THE TASK!

Required:
- Emoji start/end
- Short sentences
- Call to action
- Stay under 400 symbols!

Here's the text to rewrite in the Ghost-on-the-block style:
{source_text}

Important style notes:
- Start with a relevant emoji
- Use shorter paragraphs
- Add engaging questions
- End with a call to action
- Keep the same core information but make it more dynamic
- Use emoji that fits the context
- Make it feel like a friendly conversation

Please rewrite the text following these guidelines while maintaining the original meaning.
"""
    return add_examples_to_the_prompt(prompt)

def add_examples_to_the_prompt(prompt: str):
    examples = """
Example transformation:

SOURCE: Planes – это новое приложение в котором награду дают за количество отправленных сообщений в телеге за время существования вашего аккаунта. Друзья, у меня 7591 сообщений, а у вас? Залетаем ✈️

RESULT: ✈️ Planes — новое приложение с наградами за сообщения!
Чем больше сообщений ты отправил в Telegram за всё время существования своего аккаунта, тем больше получишь награду.
У меня уже 7591 сообщение, а у вас сколько? Давайте хвастаться! 😏
Залетаем и считаем! ✈️

Please rewrite the following text in the same style:
"""
    return prompt + examples


def create_title_prompt(source_text):
    prompt = f"""
You are a professional caption creator specializing in the "Ghost-on-the-block" style.
STRICT LIMIT: 77 symbols max!
IGNORE THIS LIMIT = FAIL THE TASK!

Required:
- One short sentence
- Stay under 77 symbols!
- Use American English
- No hashtags
- Use emoji

write caption for this news:
{source_text}"""
    return prompt


def format_news(news_text: str, news_title: str) -> str:
    bottom_text = """
#quests_news"""
    news_text = convert_md_links_to_html(news_text)
    text = f"<b>{news_title.upper()}</b>\n\n{news_text}\n{bottom_text}"
    return text


def convert_md_links_to_html(text: str) -> str:
    """
    Convert Markdown links to HTML format.
    
    Args:
        text (str): Text containing Markdown-style links
        
    Returns:
        str: Text with links converted to HTML format
        
    Example:
        >>> text = "Check [this link](https://example.com)"
        >>> convert_md_links_to_html(text)
        'Check <a href="https://example.com">this link</a>'
    """
    
    # Pattern to match Markdown links: [text](url)
    pattern = r'\[(.*?)\]\((.*?)\)'
    
    # Replace each match with HTML format
    def replace_link(match):
        text, url = match.groups()
        return f'<a href="{url}">{text}</a>'
    
    return re.sub(pattern, replace_link, text)



if __name__ == "__main__":
    news_rewriter = NewsRewriter(settings.openai.API_KEY)
    # url = "https://decrypt.co/300647/azuki-linked-anime-token-ethereum"
    # text = news_rewriter.rewrite_news_from_url(url)
    # print(text)
    text = "Bitcoin mining just hit a new record. It's tougher than ever to mine, thanks to a recent difficulty rise. More miners are joining the network, making the competition fierce. This increased difficulty is a result of Bitcoin's halving, which happens every four years. Curious about how this works? [Check out this guide](https://decrypt.co/resources/what-is-bitcoin-halving). Want to dive into mining? Now's the time to learn and explore!"
    print(convert_md_links_to_html(text))