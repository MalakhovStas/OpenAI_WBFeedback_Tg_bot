import json
from dataclasses import dataclass
from datetime import datetime

from aiogram.types import Message, CallbackQuery

from config import NUM_FEED_BUTTONS, MODE_GENERATE_ANSWER, WB_TAKE
from utils import misc_utils


@dataclass
class WBParseData:
    get_supplier_data: str = 'https://www.wildberries.ru/webapi/seller/data/short/{supplier}'
    get_items_from_supplier_id: str = 'https://catalog.wb.ru/sellers/catalog?dest=-1257786&supplier={supplier}'
    get_feedbacks2_from_items: str = 'https://feedbacks2.wb.ru/feedbacks/v1/{item_root_id}'
    get_feedbacks1_from_items: str = 'https://feedbacks1.wb.ru/feedbacks/v1/{item_root_id}'


class WBParsingManager:
    """ Класс Singleton для парсинга Wildberries """

    __instance = None
    m_utils = misc_utils

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    async def __call__(self, supplier_id: str | int, update: CallbackQuery | Message | None = None,
                       user_id: str | None = None, waiting_msgs: bool = True,
                       only_date: str | None = None) -> tuple[dict, int]:

        user_id = user_id if user_id else update.from_user.id
        if isinstance(supplier_id, str) and supplier_id.startswith('SupplierParsing'):
            supplier_id = supplier_id.lstrip('SupplierParsing')

        supplier = await self.parse_get_supplier(supplier_id, update=update, user_id=user_id)
        supplier_name = list(supplier.values())[0].get("button_name") \
            if supplier and isinstance(supplier, dict) else 'Нет данных'

        wait_msg = await self.bot.send_message(
            chat_id=user_id,
            text=f'🌐 Загружаю отзывы  магазина:'
                 f'\n<b>{supplier_name}</b>\nнемного подождите пожалуйста...'
        ) if waiting_msgs else None

        products_root_id = await self.parse_get_supplier_products(supplier_id)
        result_feedbacks, supplier_total_feeds = await self.parse_get_feedbacks_list(products_root_id=products_root_id,
                                                                                     supplier_id=supplier_id,
                                                                                     update=update, user_id=user_id,
                                                                                     only_date=only_date)

        if wait_msg:
            await self.bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)
        return result_feedbacks, supplier_total_feeds

    def __init__(self, dbase, bot, rm, ai, logger):
        self.wb_data = WBParseData
        self.dbase = dbase
        self.bot = bot
        self.requests_manager = rm
        self.ai = ai
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    async def parse_get_supplier(self, supplier_id: str | int, update: Message | CallbackQuery | None = None,
                                 user_id: int | None = None) -> dict[str, dict] | None:
        exc = None
        supplier = None
        user_id = user_id if user_id else update.from_user.id

        response = await self.requests_manager(url=self.wb_data.get_supplier_data.format(supplier=supplier_id))

        self.logger.debug(self.sign + f'-> {response=}')

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
                await self.dbase.save_suppliers(supplier, user_id=user_id)

        if not supplier:
            self.logger.warning(self.sign + f'ERROR {response=} | {exc=}')

        return supplier

    async def parse_get_supplier_products(self, supplier_id: str | int):
        exc = None
        products_root_id = dict()

        response = await self.requests_manager(self.wb_data.get_items_from_supplier_id.format(supplier=supplier_id))
        try:
            if not response.get('response'):
                data = response
            else:
                data = json.loads(response.get('response'))

            for product in data.get('data')['products']:
                products_root_id.update({product.get('root'): product.get('name')})

        except KeyError as exc:
            pass

        else:
            self.logger.debug(self.sign + f'{len(products_root_id)=}')

        if not products_root_id:
            self.logger.warning(self.sign + f'ERROR {response=} | {exc=}')

        return products_root_id

    async def parse_get_feedbacks_list(self, products_root_id: dict, supplier_id,
                                       update: Message | CallbackQuery | None = None,
                                       user_id: int | None = None, only_date: str | None = None) -> tuple[dict, int]:

        # res_products_root_id = await self.m_utils.random_choice_dict_elements(is_dict=products_root_id, num_elements=5)
        res_products_root_id = products_root_id
        total_good_steps = 0
        only_date = str(datetime.now().year) if not only_date else str(only_date)
        result_feeds = dict()
        supplier_name = f'SupplierParsing{supplier_id}'
        user_id = user_id if user_id else update.from_user.id

        wb_user = await self.dbase.wb_user_get_or_none(user_id=user_id)
        ignored_feeds = wb_user.ignored_feedbacks
        unanswered_feeds = wb_user.unanswered_feedbacks
        total_feeds_in_db = ignored_feeds | unanswered_feeds

        self.logger.debug(f'{len(total_feeds_in_db)=} | {len(unanswered_feeds.keys())=} | {len(ignored_feeds.keys())=}')

        for item_root_id, product_name in res_products_root_id.items():
            if total_good_steps >= WB_TAKE: break
            response = await self.requests_manager(
                self.wb_data.get_feedbacks1_from_items.format(item_root_id=item_root_id))

            feedbacks = response.get('feedbacks')

            if not feedbacks:
                response = await self.requests_manager(
                    self.wb_data.get_feedbacks2_from_items.format(item_root_id=item_root_id))

                feedbacks = response.get('feedbacks', list())

            self.logger.debug(self.sign + f' -> {product_name=} | {len(feedbacks)=}')

            for step, feedback in enumerate(feedbacks, 1):
                feedback_id = feedback.get('id')
                feed_answer = feedback.get('answer')
                if not feed_answer and not f"FeedbackParsing{feedback_id}" in total_feeds_in_db.keys() \
                        and feedback.get('createdDate').startswith(only_date):

                    if MODE_GENERATE_ANSWER == 'automatic' and step > NUM_FEED_BUTTONS // len(res_products_root_id):
                        break
                    else:
                        if total_good_steps >= WB_TAKE: break
                        total_good_steps += 1

                    result_feeds.update({f"FeedbackParsing{feedback_id}": {
                        'supplier': supplier_name,
                        'button_name': f"[ {feedback.get('productValuation')} ]  {feedback.get('text')[:100]}",
                        'text': feedback.get('text'),
                        'answer': feed_answer,
                        'productValuation': feedback.get('productValuation'),
                        'productName': product_name,
                        'createdDate': feedback.get('createdDate')}})

        if MODE_GENERATE_ANSWER == 'automatic':
            result_feeds = await self.ai.automatic_generate_answer_for_many_feeds(feedbacks=result_feeds)
        else:
            result_feeds = await self.m_utils.set_hint_in_answer_for_many_feeds(feedbacks=result_feeds)

        await self.dbase.save_unanswered_feedbacks(unanswered_feedbacks=result_feeds, user_id=user_id)

        supplier_total_feeds = len([feed for feed in total_feeds_in_db.values()
                                    if feed.get('supplier') == supplier_name]) + len(result_feeds)

        self.logger.debug(self.sign + f'{len(result_feeds)=} | {supplier_name=}')
        return result_feeds, supplier_total_feeds


if __name__ == '__main__':
    pass

    # inst = WBParsingManager()
    # # suppl = 258729
    # suppl = 252218
    # asyncio.run(inst(suppl))

    # wb: str = 'https://www.wildberries.ru'
    # wb_catalog: str = 'https://www.wildberries.ru/webapi/menu/main-menu-ru-ru.json'
    # wb_seller: str = 'https://www.wildberries.ru/seller/{oldID}'
    # wb_item_feeds: str = 'https://www.wildberries.ru/catalog/{}/feedbacks'
    # seller_data_short = 'https://www.wildberries.ru/webapi/seller/data/short/252218'
    # new_url: str = 'https://feedbacks2.wb.ru/feedbacks/v1/68516936'  # товары
    # new_url2: str = 'https://feedbacks2.wb.ru/feedbacks/v1/31227718'  # отзывы по id товара
    # new_url2: str = 'https://feedbacks2.wb.ru/feedbacks/v1/31227718'  # отзывы по id товара

    # items: str = "https://catalog.wb.ru/sellers/catalog?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1257786&emp=0&lang=ru&locale=ru&pricemarginCoeff=1.0&reg=0&regions=80,64,38,4,115,83,33,68,70,69,30,86,75,40,1,66,48,110,22,31,71,114,111&sort=popular&spp=0&supplier=258729"
    #
    # content_type = {"Content-Type": "application/json"}
    # user_agent = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    #                             "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36;"}
    #
    #
    # async def request(url):
    #     headers = content_type | user_agent
    #     connector = aiohttp.TCPConnector(ssl=False)
    #     async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
    #         async with session.get(url, ssl=False, timeout=20) as response:
    #             if response.content_type in ['text/html', 'text/plain']:
    #                 result = {'response': await response.text()}
    #             else:
    #                 result = await response.json()
    #         return result
