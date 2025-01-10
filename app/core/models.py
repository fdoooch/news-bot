from pydantic import BaseModel
import datetime as dt


class NewsItem(BaseModel):
    title: str
    link: str
    published_at: dt.datetime
    source: str
    category: str | None = None
    summary: str = ""
    img_link: str | None = None