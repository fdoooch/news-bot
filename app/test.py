import os
from app.core.config import settings
from app.main import _publish_news_job

async def main():

    if not os.path.exists(settings.TMP_DIR):
            os.makedirs(settings.TMP_DIR)
    await _publish_news_job()



if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
