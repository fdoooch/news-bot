import openai

from app.core.config import settings


class NewsRewriter:
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key"""
        self.client = openai.OpenAI(api_key=api_key, project=settings.openai.PROJECT_ID)
    
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
        
    def write_title(self, text: str) -> str:
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