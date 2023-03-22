import asyncio
import json
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup

# https://cutycapt.sourceforge.net/ - снимок сайта jpg, svg, pdf и пр
@dataclass
class WPParseData:
    wb: str = 'https://www.wildberries.ru'
    wb_catalog: str = 'https://www.wildberries.ru/webapi/menu/main-menu-ru-ru.json'
    wb_seller: str = 'https://www.wildberries.ru/seller/{oldID}'
    wb_item_feeds: str = 'https://www.wildberries.ru/catalog/{}/feedbacks'
    seller_data_short = 'https://www.wildberries.ru/webapi/seller/data/short/252218'
    new_url: str = 'https://feedbacks2.wb.ru/feedbacks/v1/68516936'  # товары
    new_url2: str = 'https://feedbacks2.wb.ru/feedbacks/v1/31227718'  # отзывы по id товара
    new_url2: str = 'https://feedbacks2.wb.ru/feedbacks/v1/31227718'  # отзывы по id товара

    items: str = "https://catalog.wb.ru/sellers/catalog?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1257786&emp=0&lang=ru&locale=ru&pricemarginCoeff=1.0&reg=0&regions=80,64,38,4,115,83,33,68,70,69,30,86,75,40,1,66,48,110,22,31,71,114,111&sort=popular&spp=0&supplier=258729"

standart_headers: dict = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36;"}

cookie: dict = {'Cookie': 'route=1657467309.925.11285.956039|5b63cf1668f4c654e931e4058f25bb94; ' \
                              '_wbauid=5190819891675850777; ' \
                              '___wbu=cb9520aa-e6dc-44a8-8914-3c5fd41c0039.1675850777; ' \
                              'BasketUID=dc5cc910-8939-451c-8cb4-e350233f6202; ' \
                              '__wba_s=1; __wbl=cityId=0&regionId=0&city=Москва&phone=84957755505&latitude=55,755787&longitude=37,617634&src=1; ' \
                              '__store=117673_122258_122259_125238_125239_125240_507_3158_117501_120602_120762_6158_121709_124731_130744_159402_2737_117986_1733_686_132043_161812_1193_206968_206348_205228_172430_117442_117866; ' \
                              '__region=80_64_38_4_115_83_33_68_70_69_30_86_75_40_1_66_48_110_22_31_71_111; ' \
                              '__pricemargin=1.0--; __cpns=12_3_18_15_21; __sppfix=4; ' \
                              '__dst=-1029256_-102269_-2162196_-1257786; __catalogOptions=CardSize:C516x688&Sort:Popular; ' \
                              'ncache=117673_122258_122259_125238_125239_125240_507_3158_117501_120602_120762_6158_121709_124731_130744_159402_2737_117986_1733_686_132043_161812_1193_206968_206348_205228_172430_117442_117866;' \
                              '80_64_38_4_115_83_33_68_70_69_30_86_75_40_1_66_48_110_22_31_71_111;1.0--;12_3_18_15_21;4;CardSize:C516x688&Sort:Popular;-1029256_-102269_-2162196_-1257786; ' \
                              '___wbs=a7fb4c26-464a-4d1d-934e-8dd5001e999e.1679390433; __tm=1679402357'}


async def request(url):
    headers = standart_headers
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        async with session.get(url, ssl=False, timeout=20) as response:
                # result = await response.text()
            if response.content_type == 'text/html':
                result = {'response': await response.text()}
            else:
                result = await response.json()
        return result


# page = asyncio.run(request(url=WPParseData.wb_seller.format(oldID=258729)))
page = asyncio.run(request(url=WPParseData.new_url2))
# page = asyncio.run(request(url=WPParseData.items))
print(type(page))
print(json.dumps(page, indent=4, ensure_ascii=False))
# soup = BeautifulSoup(page, "html.parser")
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

# {
#     "Supplier727553e6-1c20-45af-8f93-031dac28cb1e": {
#         "button_name": "Краев Иван Кириллович",
#         "fullName": "Индивидуальный предприниматель Краев Иван Кириллович",
#         "general": "Краев Иван Кириллович",
#         "id": "727553e6-1c20-45af-8f93-031dac28cb1e",
#         "mode": "API",
#         "name": "Vanijo",
#         "oldID": 252218
#     },
#     "Supplierb541a87c-d482-4161-9f30-5edc1fded445": {
#         "button_name": "Андреева Татьяна Федоровна",
#         "fullName": "Индивидуальный предприниматель Андреева Татьяна Федоровна",
#         "general": "Андреева Татьяна Федоровна",
#         "id": "b541a87c-d482-4161-9f30-5edc1fded445",
#         "mode": "API",
#         "name": "ИП Андреева Т. Ф.",
#         "oldID": 258729
#     }
# }