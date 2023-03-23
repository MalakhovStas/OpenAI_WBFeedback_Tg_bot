import asyncio
import json
import time
from dataclasses import dataclass
import aiohttp
from aiogram.types  import Message, CallbackQuery
from loguru import logger
from bs4 import BeautifulSoup

# https://cutycapt.sourceforge.net/ - снимок сайта jpg, svg, pdf и пр
@dataclass
class WBParseData:
    get_supplier_data: str = 'https://www.wildberries.ru/webapi/seller/data/short/{supplier}'
    get_items_from_supplier_id: str = 'https://catalog.wb.ru/sellers/catalog?dest=-1257786&supplier={supplier}'
    get_feedbacks2_from_items: str = 'https://feedbacks2.wb.ru/feedbacks/v1/{item_root_id}'
    get_feedbacks1_from_items: str = 'https://feedbacks1.wb.ru/feedbacks/v1/{item_root_id}'

    # wb: str = 'https://www.wildberries.ru'
    # wb_catalog: str = 'https://www.wildberries.ru/webapi/menu/main-menu-ru-ru.json'
    # wb_seller: str = 'https://www.wildberries.ru/seller/{oldID}'
    # wb_item_feeds: str = 'https://www.wildberries.ru/catalog/{}/feedbacks'
    # seller_data_short = 'https://www.wildberries.ru/webapi/seller/data/short/252218'
    # new_url: str = 'https://feedbacks2.wb.ru/feedbacks/v1/68516936'  # товары
    # new_url2: str = 'https://feedbacks2.wb.ru/feedbacks/v1/31227718'  # отзывы по id товара
    # new_url2: str = 'https://feedbacks2.wb.ru/feedbacks/v1/31227718'  # отзывы по id товара

    # items: str = "https://catalog.wb.ru/sellers/catalog?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1257786&emp=0&lang=ru&locale=ru&pricemarginCoeff=1.0&reg=0&regions=80,64,38,4,115,83,33,68,70,69,30,86,75,40,1,66,48,110,22,31,71,114,111&sort=popular&spp=0&supplier=258729"


content_type = {"Content-Type": "application/json"}
user_agent = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36;"}
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
    headers = content_type | user_agent
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        async with session.get(url, ssl=False, timeout=20) as response:
            if response.content_type in ['text/html', 'text/plain']:
                result = {'response': await response.text()}
            else:
                result = await response.json()
        return result


class WBParsingManager:
    """ Класс Singleton для парсинга Wildberries """

    __instance = None
    # m_utils = misc_utils
    # wb_data = WBParseData
    # logger = logger
    # sign = 'Подпись класса: '

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    async def __call__(self, supplier_id, update):
        supplier = await self.parse_get_supplier(supplier_id, update=update)
        # products_root_id = await self.parse_get_supplier_products(supplier_id)
        # result_feedbacks = await self.parse_get_supplier_feedbacks(products_root_id=products_root_id, supplier_id=suppl)
        # return result_feedbacks
        return supplier

    def __init__(self, dbase, rm, ai, logger):
        self.wb_data = WBParseData
        self.requests_manager = rm
        self.dbase = dbase
        self.ai = ai
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    async def parse_get_supplier(self, supplier_id: str | int,
                                 update: Message | CallbackQuery | None = None, user_id: int | None = None):
        exc = None
        supplier = None
        user_id = user_id if user_id else update.from_user.id

        # response = await request(self.wb_data.get_supplier_data.format(supplier=supplier_id))
        response = await self.requests_manager(url=self.wb_data.get_supplier_data.format(supplier=supplier_id))

        self.logger.debug(self.sign + f'parse_get_supplier -> response: {response}')

        if response and isinstance(response, dict) and response.get('id'):
            try:
                supplier = {f"SupplierParsing{response['id']}":
                                    {'button_name': response['fineName'] if response['fineName'] else response['name'],
                                     'mode': 'PARSING',  # Режим работы с магазином API или PARSING
                                     'id': response['id'],  # "727553e6-1c20-45af-8f93-031dac28cb1e"
                                     'oldID': response['id'],  # 252218 нужно при парсинге
                                     'name': response['name'],  # "ИП Андреева Т. Ф."
                                     'general': response['fineName'],  # "Андреева Т. Ф."
                                     'fullName': response['fineName']  # "Андреева Т. Ф."
                                     }
                            }
            except KeyError as exc:
                pass
            else:
                self.dbase.save_suppliers(supplier, user_id=user_id)
                pass

        if not supplier:
            self.logger.warning(self.sign + f'ERROR parse_get_supplier, {response=} | {exc=}')

        return supplier

    async def parse_get_supplier_products(self, supplier_id: str | int):
        exc = None
        products_root_id = dict()

        response = await request(self.wb_data.get_items_from_supplier_id.format(supplier=supplier_id))
        try:

            data = json.loads(response.get('response'))

            for product in data.get('data')['products']:
                products_root_id.update({product.get('root'): product.get('name')})

        except KeyError as exc:
            pass

        else:
            self.logger.debug(self.sign + f'parse_get_supplier_products -> num products: {len(products_root_id)}')

        if not products_root_id:
            self.logger.warning(self.sign + f'ERROR parse_get_supplier_products, {response=} | {exc=}')

        return products_root_id

    async def parse_get_supplier_feedbacks(self, products_root_id: dict, supplier_id,
                                           update: Message | CallbackQuery | None = None, user_id: int | None = None):
        total_feedbacks = 0
        result_feedbacks = dict()

        for item_root_id, product_name in products_root_id.items():
            # item_root_id = next(iter(item))
            # product_name = item[item_root_id]
            # print(item_root_id, product_name)

            response = await request(self.wb_data.get_feedbacks1_from_items.format(item_root_id=item_root_id))
            feedbacks = response.get('feedbacks')
            # print('feedbacks1', True if feedbacks else False)
            if not feedbacks:
                response = await request(self.wb_data.get_feedbacks2_from_items.format(item_root_id=item_root_id))
                feedbacks = response.get('feedbacks')
                # print('feedbacks2', True if feedbacks else False)

            for feedback in feedbacks:
                if not feedback.get('answer') and feedback.get('createdDate').startswith('2023'):
                    total_feedbacks += 1

                    # print(feedback.get('answer'), type(feedback.get('answer')))
                    # print(feedback)
                    result_feedbacks.update({f"Feedback{feedback.get('id')}": {
                        'supplier': f"Supplier{supplier_id}",
                        'button_name': f"[ {feedback.get('productValuation')} ]  {feedback.get('text')[:100]}",
                        'text': feedback.get('text'),
                        'answer': feedback.get('answer'),
                        'productValuation': feedback.get('productValuation'),
                        'productName': product_name,
                        'createdDate': feedback.get('createdDate')}})


        # data = [self.ai.reply_many_feedbacks(feed_name=feed_name, feedback=feed_data.get('text'))
        #         for feed_name, feed_data in result_feedbacks.items()]

        # list_result = await asyncio.gather(*data)
        # await asyncio.sleep(0.1)
        # [result_feedbacks.get(feed_name).update({'answer': answer}) for feed_name, answer in list_result]

        print(f'total_feedbacks:{total_feedbacks}')
        # print(json.dumps(result_feedbacks, indent=4, ensure_ascii=False))

        return result_feedbacks


if __name__ == '__main__':

    inst = WBParsingManager()
    # suppl = 258729
    suppl = 252218
    asyncio.run(inst(suppl))
