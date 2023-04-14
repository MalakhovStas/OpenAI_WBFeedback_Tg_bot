import asyncio
import functools
from dataclasses import dataclass, field
from datetime import datetime
from types import FunctionType
from aiogram.types import CallbackQuery, Message

from config import WB_TAKE, MODE_GENERATE_ANSWER
from utils import misc_utils


@dataclass
class WBData:
    """Отправляем phone получаем token для ввода кода"""
    """wb api: "https://seller.wildberries.ru/passport/api/v2/auth/login_by_phone/"""
    """{"phone": "111111111", "is_terms_and_conditions_accepted": True}"""
    send_phone_url: str = 'http://65.21.229.152:1488/auth/login-by-phone'
    # send_phone_url: str = "https://seller.wildberries.ru/passport/api/v2/auth/login_by_phone/"

    """Отправляем код из смс и token -> получаем sellerToken(сессионный в любой момент упадет)"""
    """wb_api: https://seller.wildberries.ru/passport/api/v2/auth/login"""
    """data = {"options": {"notify_code": sms_code}, "token": token}"""
    send_code_from_sms_url: str = 'http://65.21.229.152:1488/auth/enter-sms'
    # send_code_from_sms_url: str = 'https://seller.wildberries.ru/passport/api/v2/auth/login'

    """Отправляем sellerToken -> получаем passportToken(живет 7-10дней нужен для восстановления sellerToken)"""
    get_passportToken_url: str = 'http://65.21.229.152:1488/auth/passport'

    """Отправляем passportToken -> получаем sellerToken (этот запрос если упадёт sellerToken)"""
    get_sellerToken_from_passportToken_url: str = 'http://65.21.229.152:1488/auth/seller'

    """Проверка действительности токенов"""
    introspect_token_url: str = 'http://65.21.229.152:1488/auth/introspect'

    """Получаем список кабинетов из которых возьмём id -> это и есть x-suplier-id"""
    get_suppliers_url: str = 'https://seller.wildberries.ru/ns/suppliers/suppliers-portal-core/suppliers'

    """Отправляем ответ на отзыв"""
    send_answer_feedback: str = 'https://seller.wildberries.ru/ns/api/suppliers-portal-feedbacks-questions' \
                                '/api/v1/feedbacks'

    get_suppliers_data: list = field(default_factory=lambda: [
        {"method": "getUserSuppliers", "params": {}, "id": "json-rpc_4", "jsonrpc": "2.0"}])

    def get_feedback_list_url(self, take: int | str | None = None):
        """Получаем список отзывов параметр take - количество отзывов"""
        return "https://seller.wildberries.ru/ns/api/suppliers-portal-feedbacks-questions/api/v1/" \
               "feedbacks?hasSupplierComplaint&isAnswered=false&metaDataKeyMustNot=norating&nmId=&" \
               f"order=dateDesc&skip=0&take={take if take else 10}"""


class WBAPIManager:
    """ Класс Singleton для работы с API Wildberries и соблюдения принципа DRY """

    __instance = None
    m_utils = misc_utils

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, dbase, rm, ai, logger):
        self.wb_data = WBData()
        self.requests_manager = rm
        self.dbase = dbase
        self.ai = ai
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    @staticmethod
    def wrapper_checking_seller_token_before_sending_request(method: FunctionType) -> FunctionType:
        @functools.wraps(method)
        async def wrapper(*args, **kwargs) -> FunctionType:
            none_results = {'get_passport_token': None,
                            'get_suppliers': None,
                            'get_feedback_list': dict(),
                            'send_feedback': False}
            self = args[0]
            update = kwargs.get('update')
            user_id = kwargs.get('user_id') if kwargs.get('user_id') else update.from_user.id

            wb_user = await self.dbase.wb_user_get_or_none(user_id=user_id)
            seller_token = wb_user.sellerToken
            passport_token = wb_user.passportToken
            wb_user_id = wb_user.WB_user_id

            check_result = await self.introspect_seller_token(seller_token=seller_token,
                                                              update=update, user_id=user_id)

            if check_result and not passport_token:
                passport_token = await self.get_passport_token(seller_token=seller_token,
                                                               update=update, user_id=user_id)

            if passport_token and (not check_result or check_result != wb_user_id):
                seller_token = await self.get_seller_token_from_passport_token(passport_token=passport_token,
                                                                               update=update, user_id=user_id)
                # Для сохранения в БД wb_user_id
                await self.introspect_seller_token(seller_token=seller_token, update=update, user_id=user_id)

            if seller_token:
                kwargs['seller_token'] = seller_token
                result = await method(*args, **kwargs)
            else:
                result = none_results.get(method.__name__)

            return result
        return wrapper

    # def decorate_methods(self):
    #     for attr_name in self.__class__.__dict__:
    #         # print("WBAPIManager decorate_methods!!!", attr_name)
    #
    #         if not attr_name.startswith('__') and attr_name not in [
    #             'check_data', 'decorate_methods', 'get_token', 'send_phone_number', 'send_sms_code',
    #                 'get_seller_token_from_passport_token', 'introspect_seller_token',
    #                     'wrapper_checking_seller_token_before_sending_request']:
    #
    #             method = self.__class__.__getattribute__(self.__class__, attr_name)
    #             if type(method) is FunctionType:
    #                 setattr(self, attr_name, self.wrapper_checking_seller_token_before_sending_request(method))
    #                 print("WBAPIManager decorate_methods2!!!", attr_name)

    @staticmethod
    async def get_token(response_request: dict) -> str | None:
        if response_request and response_request.get('success'):
            if response := response_request.get('response'):
                if token := response.get('token'):
                    return token

    async def send_phone_number(self, phone_number: str, update: Message | CallbackQuery | None = None,
                                user_id: int | None = None) -> str | None:
        """Отправляем phone получаем token для ввода кода из sms"""
        sms_token = None
        user_id = user_id if user_id else update.from_user.id
        if phone_number := await self.m_utils.check_data(phone_number):
            response_request = await self.requests_manager(
                url=self.wb_data.send_phone_url,
                method='post',
                data={"phoneNumber": int(phone_number)}
                # data={"phone": int(phone_number), "is_terms_and_conditions_accepted": True},
            )
            self.logger.debug(self.sign + f'send phoneNumber: {phone_number}, response: {response_request}')
            if sms_token := await self.get_token(response_request):
                await self.dbase.save_phone_number_and_sms_token(phone_number, sms_token, user_id=user_id)
        return sms_token

    async def send_sms_code(self, sms_code: str, sms_token: str, update: Message | CallbackQuery | None = None,
                            user_id: int | None = None) -> str | None:
        """Отправляем код из смс и token -> получаем sellerToken(сессионный в любой момент упадет)"""
        seller_token = None
        user_id = user_id if user_id else update.from_user.id
        if sms_code := await self.m_utils.check_data(sms_code):
            response_request = await self.requests_manager(
                url=self.wb_data.send_code_from_sms_url,
                method='post',
                data={"code": sms_code, "token": sms_token}
            )
            self.logger.debug(self.sign + f'send sms code: {sms_code}, response: {response_request}')
            if seller_token := await self.get_token(response_request):
                await self.dbase.save_seller_token(seller_token, user_id=user_id)
        return seller_token

    async def get_seller_token_from_passport_token(self, passport_token: str,
                                                   update: Message | CallbackQuery | None = None,
                                                   user_id: int | None = None) -> str | None:
        """Отправляем passportToken -> получаем sellerToken (этот запрос если упадёт sellerToken)"""
        seller_token = None
        user_id = user_id if user_id else update.from_user.id

        if passport_token:
            response_request = await self.requests_manager(
                url=self.wb_data.get_sellerToken_from_passportToken_url,
                method='post',
                data={"passportToken": passport_token}
            )
            self.logger.debug(self.sign + f'get_seller_token_from_passport_token -> send passportToken, '
                                          f'response: {response_request}')
            if seller_token := await self.get_token(response_request):
                await self.dbase.save_seller_token(seller_token, user_id=user_id)
        return seller_token

    async def introspect_seller_token(self, seller_token: str, update: Message | CallbackQuery | None = None,
                                      user_id: int | None = None) -> str | bool:
        """ Проверка действительности sellerToken возвращает WB userId | False """
        user_id = user_id if user_id else update.from_user.id

        response_request = await self.requests_manager(
            url=self.wb_data.introspect_token_url,
            method='post',
            data={"type": "seller", 'token': seller_token}
        )

        self.logger.debug(self.sign + f'introspect sellerToken, response: {response_request}')
        if response_request and response_request.get('success'):
            if response := response_request.get('response'):
                if wb_user_id := response.get('userId'):
                    await self.dbase.save_wb_user_id(wb_user_id=wb_user_id, user_id=user_id)
                    return wb_user_id
        return False

    async def get_passport_token(self, seller_token: str, update: Message | CallbackQuery | None = None,
                                 user_id: int | None = None) -> str | None:

        """Отправляем sellerToken -> получаем passportToken(живет 7-10дней нужен для восстановления sellerToken)"""
        passport_token = None
        user_id = user_id if user_id else update.from_user.id

        if seller_token:
            response_request = await self.requests_manager(
                url=self.wb_data.get_passportToken_url,
                method='post',
                data={"sellerToken": seller_token}
            )
            self.logger.debug(self.sign + f'get_passport_token -> send sellerToken, response: {response_request}')
            if passport_token := await self.get_token(response_request):
                await self.dbase.save_passport_token(passport_token, user_id=user_id)
        return passport_token

    @wrapper_checking_seller_token_before_sending_request
    async def get_suppliers(self, seller_token: str, update: Message | CallbackQuery | None = None,
                            user_id: int | None = None) -> dict | None:
        """Отправляем sellerToken получаем список кабинетов из которых возьмём id -> это и есть x-supplier-id"""
        exc = None
        suppliers = None
        user_id = user_id if user_id else update.from_user.id

        response = await self.requests_manager(
            url=self.wb_data.get_suppliers_url,
            method='post',
            data=self.wb_data.get_suppliers_data,
            headers={"Cookie": f"WBToken={seller_token}"},
            add_headers=True
        )
        self.logger.debug(self.sign + f'send sellerToken -> {response=}')
        if response:
            try:
                suppliers = {
                    f"Supplier{supplier['id']}":
                        {'button_name': supplier['general'] if supplier['general'] else supplier['name'],
                         'mode': 'API',  # Режим работы с магазином API или PARSING
                         'id': supplier['id'],  # "727553e6-1c20-45af-8f93-031dac28cb1e"
                         'oldID': supplier['oldID'],  # 252218 нужно при парсинге
                         'name': supplier['name'],  # "Vanijo"
                         'general': supplier['general'],  # "Краев Иван Кириллович"
                         'fullName': supplier['fullName']  # "Индивидуальный предприниматель Краев Иван Кириллович"
                         } for supplier in response[0]['result']['suppliers']
                }

            except KeyError as exc:
                self.logger.warning(self.sign + f'ERROR -> {exc=}')
            else:
                await self.dbase.save_suppliers(suppliers, user_id=user_id)

        if not suppliers:
            self.logger.warning(self.sign + f'BAD -> {suppliers=} | {response=}')

        self.logger.debug(self.sign + f'OK -> return {suppliers=}')
        return suppliers

    @wrapper_checking_seller_token_before_sending_request
    async def get_feedback_list(self, supplier: dict[str, str] | str, seller_token: str | None = None,
                                take: int | None = None, update: Message | CallbackQuery | None = None,
                                user_id: int | None = None,
                                only_date: str | None = None) -> tuple[dict[str, dict] | dict, int]:
        """ Получаем список неотвеченных отзывов от WB в количестве(config -> WB_TAKE + len(ignored_feedbacks))
            выбираем только те, которые не в списке игнорируемых отзывов в БД -> таблица wildberries ->
            ignored_feedbacks и неотвеченных отзывов -> unanswered_feedback. Затем асинхронно генерируем
            ответ на отзывы с помощью OpenAiManager, результат возвращаем и сохраняем в
            БД -> wildberries -> unanswered_feedbacks и """

        only_date = str(datetime.now().year) if not only_date else str(only_date)
        take = WB_TAKE if not take else take
        ignored_feeds = dict()
        unanswered_feeds = dict()
        feedbacks_from_wb_api = list()
        result_feedbacks = dict()
        user_id = user_id if user_id else update.from_user.id

        if isinstance(supplier, dict):
            x_supplier_id = list(supplier.keys())[0].lstrip('Supplier')
            supplier_name = list(supplier.values())[0]
        else:
            x_supplier_id = supplier.lstrip('Supplier') if supplier else ''
            supplier_name = supplier if supplier else ''

        wb_user = await self.dbase.wb_user_get_or_none(user_id=user_id)
        seller_token = wb_user.sellerToken if not seller_token else seller_token
        ignored_feeds = wb_user.ignored_feedbacks
        unanswered_feeds = wb_user.unanswered_feedbacks
        total_feeds_in_db = ignored_feeds | unanswered_feeds

        self.logger.debug(f'{len(ignored_feeds.keys())=} | {len(unanswered_feeds.keys())=} '
                          f'| {len(total_feeds_in_db)=}')

        response_request = await self.requests_manager(
            url=self.wb_data.get_feedback_list_url(take=len(total_feeds_in_db) + take),
            method='get',
            headers={"Cookie":  f"x-supplier-id={x_supplier_id}; WBToken={seller_token};"},
            add_headers=True
        )

        if response_request:
            if data := response_request.get('data'):
                feedbacks_from_wb_api = data.get('feedbacks')

        self.logger.debug(self.sign + f'{len(feedbacks_from_wb_api)=}')

        for feedback in feedbacks_from_wb_api:
            feedback_id = feedback.get('id')
            if not f"Feedback{feedback_id}" in total_feeds_in_db.keys() and \
                    feedback.get('createdDate').startswith(only_date):
                result_feedbacks.update(
                    {f"Feedback{feedback_id}": {
                     'supplier': f"Supplier{x_supplier_id}",
                     'button_name': f"[ {feedback.get('productValuation')} ]  {feedback.get('text')[:100]}",
                     'text': feedback.get('text'), 'answer': feedback.get('answer'),
                     'productValuation': feedback.get('productValuation'),
                     'productName': feedback.get('productDetails')['productName'],
                     'createdDate': feedback.get('createdDate')}}
                )

        if MODE_GENERATE_ANSWER == 'automatic':
            result_feedbacks = await self.ai.automatic_generate_answer_for_many_feeds(feedbacks=result_feedbacks,
                                                                                      user_id=user_id)
        else:
            result_feedbacks = await self.m_utils.set_hint_in_answer_for_many_feeds(feedbacks=result_feedbacks)

        await self.dbase.save_unanswered_feedbacks(unanswered_feedbacks=result_feedbacks, user_id=user_id)
        self.logger.debug(self.sign + f'{len(result_feedbacks)=} | {supplier_name=}')

        supplier_total_feeds = len([feed for feed in total_feeds_in_db.values()
                                    if feed.get('supplier') == supplier_name]) + len(result_feedbacks)

        return result_feedbacks, supplier_total_feeds

    @wrapper_checking_seller_token_before_sending_request
    async def send_feedback(self, seller_token: str, x_supplier_id: str,
                            feedback_id: str, feedback_answer__text: str, update: CallbackQuery | Message) -> bool:

        """Отправляем ответ на отзыв"""
        response_request = await self.requests_manager(
            url=self.wb_data.send_answer_feedback,
            method='patch',
            headers={"Cookie": f"x-supplier-id={x_supplier_id}; WBToken={seller_token};"},
            data={"id": feedback_id, "text": feedback_answer__text},
            add_headers=True
        )
        # варианты ответа сервера
        # {'data': None, 'error': True, 'errorText': 'Не найден отзыв 75t6oYBTZEOO9f5RrfJ', 'additionalErrors': None}
        # {'data': None, 'error': False, 'errorText': '', 'additionalErrors': None}

        error = response_request.get('error')
        error_text = response_request.get('errorText')

        if response_request and error is False:
            result = True
        else:
            result = False

        self.logger.info(self.sign + f'send_feedback {result=} | {error=} | {error_text=}')

        return result


if __name__ == '__main__':
    pass
