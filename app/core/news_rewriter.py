import openai
import logging

from app.core.config import settings
from app.core.exceptions import RewritedNewsIsTooLongError

logger = logging.getLogger(settings.LOGGER_NAME)


class NewsRewriter:
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key"""
        self.client = openai.OpenAI(api_key=api_key, project=settings.openai.PROJECT_ID)


    def rewrite_news(self, news_text: str, news_title: str, max_news_text_len: int = 1000, max_rewriting_tries: int = 3):
        for _ in range(max_rewriting_tries):
            rewrited_text = self.rewrite_text(news_text)
            rewrited_title = self.rewrite_title(news_title)
            news =  self.gather_news(rewrited_text, rewrited_title)
            if len(news) <= max_news_text_len:
                return news
            logger.warning("Rewrited news is too long. Trying again...")
            logger.info(f"REWRITED TEXT: {news}")
        raise RewritedNewsIsTooLongError(
            error_message="Unable to rewrite news in setted length",
            original_news=f"{news_title}\n{news_text}",
            rewrited_news=news,
            rewrited_news_length=len(news)
        )
        
    
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
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in rewriting text: {str(e)}")
            return text  # Return original text if rewriting fails
        
    def rewrite_title(self, text: str) -> str:
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
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error in writing title: {str(e)}")
            return ""  # Return empty string if title writing fails
        
    def gather_news(self, news_text: str, news_title: str) -> str:
        bottom_text = """
#quests_news"""
        text = f"<b>{news_title.upper()}</b>\n\n{news_text}\n{bottom_text}"
        return text
        

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

write caption for this text:
{source_text}"""
    return prompt