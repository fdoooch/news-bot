import os
from app.core.config import settings
import json

async def main():

    if not os.path.exists(settings.TMP_DIR):
            os.makedirs(settings.TMP_DIR)
    # await _publish_news_job()
    with open(f"{settings.APP_DIR}/publishing_schedule.json", "r") as f:
        schedule = json.load(f)
    print(schedule)



if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
