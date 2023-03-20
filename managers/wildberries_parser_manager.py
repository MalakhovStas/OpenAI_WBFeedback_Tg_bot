import asyncio
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup

async def request(url):
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36;"}
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        async with session.get(url, ssl=False, timeout=20) as response:
                result = await response.text()
            # if response.content_type == 'text/html':
            #     result = {'response': await response.text()}
            # else:
            #     result = await response.json()
        return result

@dataclass
class WPParseData:
    wb: str = 'https://www.wildberries.ru'
    wb_catalog: str = 'https://www.wildberries.ru/webapi/menu/main-menu-ru-ru.json'
    wb_seller: str = 'https://www.wildberries.ru/seller/{oldID}'
    wb_item_feeds: str = 'https://www.wildberries.ru/catalog/{}/feedbacks'
    seller_data_short = 'https://www.wildberries.ru/webapi/seller/data/short/252218'

page = asyncio.run(request(url=WPParseData.wb_seller.format(oldID=252218)))
# print(type(page))
soup = BeautifulSoup(page, "html.parser")
# print(soup.find('div', class_="product-card__img-wrap img-plug j-thumbnail-wrap"))
# print(soup.find('div', class_="main__container"))
# print(soup.find('div', id="catalog"))

#1. https://www.wildberries.ru/seller/{oldID} oldID - это номер который введет человек
    # список товаров
        #/html/body/div[1]/main/div[2]/div/div[2]/div/div[5]/div[1]/div/div fullxpath
        ##catalog > div.catalog-page__main.new-size > div.catalog-page__content > div > div selector
        # товар class data-nm-id=1447022027 нужен этот id
            #c144702027 selector
            # //*[@id="c144702027"] xpath
            # /html/body/div[1]/main/div[2]/div/div[2]/div/div[5]/div[1]/div/div/div[1] fullxpath

#2. https://www.wildberries.ru/catalog/{data-nm-id}/feedbacks - data-nm-id это то что мы нашли выше

# https://www.wildberries.ru/catalog/1447022027/feedbacks

