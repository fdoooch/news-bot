# TODO
[v] спарсить ленту новостей
[ ] отфильтровать новости по категории и по дате
[ ] взять последнюю новость в каждой категории

## TASK
написать бота для телеграмм который бы мониторил выход новостей отсюда
https://decrypt.co/news/cryptocurrencies
https://decrypt.co/news/gaming

Брал бы только картинку первую, конвертик ее в jpg, заголовок и текст - загонял в chatgpt для рерайта по промту и постил в тг канал - снизу бы добавлял ссылки блок и хештег

Схема такая:
- в конце дня заходит в указанные категории
- если есть пост за текущую дату то открывает пост, берет заголовок с описанием и картинку
- отправляет на рерайт по промту в чатгпт
- картинку конвертит в jpg

Пост в канал
- вставляет полученный текст от чатгпт, внизу блок ссылками и хештег
- добавляет картинку
- постит


Промт для ChatGPT 
Rewrite the text briefly, up to 500 characters, in the style of Ghost on the Block.