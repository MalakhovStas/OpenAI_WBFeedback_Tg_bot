import json
from dataclasses import dataclass, field


@dataclass
class WBData:
    """Отправляем phone получаем token для ввода кода"""
    """wb api: "https://seller.wildberries.ru/passport/api/v2/auth/login_by_phone/"""
    """{"phone": "111111111", "is_terms_and_conditions_accepted": True}"""
    send_phone_url: str = 'http://65.21.229.152:1488/auth/login-by-phone'

    """Отправляем код из смс и token -> получаем sellerToken(сессионный в любой момент упадет)"""
    """wb_api: https://seller.wildberries.ru/passport/api/v2/auth/login"""
    """data = {"options": {"notify_code": sms_code}, "token": token}"""
    send_code_from_sms_url: str = 'http://65.21.229.152:1488/auth/enter-sms'

    """Отправляем sellerToken -> получаем passportToken(живет 7-10дней нужен для восстановления sellerToken)"""
    get_passportToken_url: str = 'http://65.21.229.152:1488/auth/passport'

    """Отправляем passportToken -> получаем sellerToken (этот запрос если упадёт sellerToken)"""
    get_sellerToken_from_passportToken_url: str = 'http://65.21.229.152:1488/auth/seller'

    """Проверка действительности токенов"""
    introspect_token_url: str = 'http://65.21.229.152:1488/auth/introspect'

    """Получаем список кабинетов из которых возьмём id -> это и есть x-suplier-id"""
    get_suppliers_url: str = 'https://seller.wildberries.ru/ns/suppliers/suppliers-portal-core/suppliers'

    """Получаем список отзывов параметр take - количество отзывов"""
    get_feedback_list_url: str = "https://seller.wildberries.ru/ns/api/suppliers-portal-feedbacks-questions/api/v1/" \
                                 "feedbacks?hasSupplierComplaint&isAnswered=false&metaDataKeyMustNot=norating&nmId=&" \
                                 "order=dateDesc&skip=0&take=10"""
    """Отправляем ответ на отзыв"""
    send_answer_feedback: str = 'https://seller.wildberries.ru/ns/api/suppliers-portal-feedbacks-questions' \
                                '/api/v1/feedbacks'

    get_suppliers_data: list = field(default_factory=lambda: [
        {"method": "getUserSuppliers", "params": {}, "id": "json-rpc_4", "jsonrpc": "2.0"}])


class WBAPIManager:
    """ Класс Singleton для работы с API Wildberries и соблюдения принципа DRY """

    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, dbase, rm, logger):
        self.wb_data = WBData()
        self.requests_manager = rm
        self.dbase = dbase
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    @staticmethod
    async def check_data(data: str) -> str | None:
        data = data.replace(' ', '').replace('-', '').lstrip('+')
        return data if data.isdigit() else None

    @staticmethod
    async def get_token(response_request: dict) -> str | None:
        if response_request and response_request.get('success'):
            if response := response_request.get('response'):
                if token := response.get('token'):
                    return token

    async def send_phone_number(self, phone_number: str, update) -> str | None:
        """Отправляем phone получаем token для ввода кода из sms"""
        sms_token = None
        if phone_number := await self.check_data(phone_number):
            response_request = await self.requests_manager(
                url=self.wb_data.send_phone_url,
                method='post',
                data={"phoneNumber": int(phone_number)}
            )
            self.logger.debug(self.sign + f'send phoneNumber: {phone_number}, response: {response_request}')
            if sms_token := await self.get_token(response_request):
                self.dbase.save_phone_number_and_sms_token(phone_number, sms_token, user_id=update.from_user.id)
        return sms_token

    async def send_sms_code(self, sms_code: str, sms_token: str, update) -> str | None:
        """Отправляем код из смс и token -> получаем sellerToken(сессионный в любой момент упадет)"""
        seller_token = None
        if sms_code := await self.check_data(sms_code):
            response_request = await self.requests_manager(
                url=self.wb_data.send_code_from_sms_url,
                method='post',
                data={"code": sms_code, "token": sms_token}
            )
            self.logger.debug(self.sign + f'send sms code: {sms_code}, response: {response_request}')
            if seller_token := await self.get_token(response_request):
                self.dbase.save_seller_token(seller_token, user_id=update.from_user.id)
        return seller_token

    async def get_passport_token(self, seller_token: str, update) -> str | None:
        """Отправляем sellerToken -> получаем passportToken(живет 7-10дней нужен для восстановления sellerToken)"""
        passport_token = None
        if seller_token:
            response_request = await self.requests_manager(
                url=self.wb_data.get_passportToken_url,
                method='post',
                data={"sellerToken": seller_token}
            )
            self.logger.debug(self.sign + f'get_passport_token -> send sellerToken, response: {response_request}')
            if passport_token := await self.get_token(response_request):
                self.dbase.save_passport_token(passport_token, user_id=update.from_user.id)
        return passport_token

    async def get_seller_token_from_passport_token(self, passport_token: str, update) -> str | None:
        """Отправляем passportToken -> получаем sellerToken (этот запрос если упадёт sellerToken)"""
        seller_token = None
        if passport_token:
            response_request = await self.requests_manager(
                url=self.wb_data.get_sellerToken_from_passportToken_url,
                method='post',
                data={"passportToken": passport_token}
            )
            self.logger.debug(self.sign + f'get_seller_token_from_passport_token -> send passportToken, response: {response_request}')
            if seller_token := await self.get_token(response_request):
                self.dbase.save_seller_token(seller_token, user_id=update.from_user.id)
        return seller_token

    async def introspect_seller_token(self, seller_token: str) -> str | bool:
        """ Проверка действительности sellerToken возвращает WB userId | False """
        response_request = await self.requests_manager(
            url=self.wb_data.introspect_token_url,
            method='post',
            data={"type": "seller", 'token': seller_token}
        )
        self.logger.debug(self.sign + f'introspect sellerToken, response: {response_request}')
        if response_request and response_request.get('success'):
            if response := response_request.get('response'):
                if wb_user_id := response.get('userId'):
                    #TODO возможно тут будет нужна проверка соответствия sellerToken и WB_user_id в БД
                    return wb_user_id
        return False

    async def get_suppliers(self, seller_token: str, update) -> dict | None:
        """Отправляем sellerToken получаем список кабинетов из которых возьмём id -> это и есть x-supplier-id"""
        exc = None
        suppliers = None
        response_request = await self.requests_manager(
            url=self.wb_data.get_suppliers_url,
            method='post',
            data=self.wb_data.get_suppliers_data,
            headers={"Cookie": f"WBToken={seller_token}"},
            add_headers=True
        )
        self.logger.debug(self.sign + f'get_suppliers -> send sellerToken, response: {response_request}')
        # TODO тут нужна настройка
        if response_request:
            try:
                # suppliers = {supplier['general']: supplier['id'] for supplier in
                #              response_request[0]['result']['suppliers']}

                suppliers = {supplier['id']: {'name': supplier['general']}
                             for supplier in response_request[0]['result']['suppliers']}
            except KeyError as exc:
                pass
            else:
                self.dbase.save_suppliers(suppliers, user_id=update.from_user.id)
                pass
        if not suppliers:
            self.logger.debug(self.sign + f'ERROR get_suppliers, response: {response_request}, "exc:" {exc}')
        return suppliers

    async def get_feedback_list(self, seller_token: str, supplier: dict[str, str]) -> dict[str, dict]:
        """Получаем список отзывов"""
        feedbacks = []
        response_request = await self.requests_manager(
            url=self.wb_data.get_feedback_list_url,
            method='get',
            headers={"Cookie":  f"x-supplier-id={list(supplier.keys())[0]}; WBToken={seller_token};"},
            add_headers=True
        )

        if response_request:
            if data := response_request.get('data'):
                feedbacks = data.get('feedbacks')
        result = {feedback.get('id'): {'text': feedback.get('text'), 'answer': feedback.get('answer'),
                                       'productValuation': feedback.get('productValuation'),
                                       'productName': feedback.get('productDetails')['productName'],
                                       "createdDate": feedback.get('createdDate')} for feedback in feedbacks}

        # print(self.sign + f'get_feedback_list -> send x-supplier-id from supplier: "{supplier.values()}" '
        #                   f'response: {json.dumps(result, indent=4, ensure_ascii=False)}')
        # self.dbase.save_unanswered_feedbacks(result, user_id=update.from_user.id)
        return result

    def send_feedback(self, seller_token, x_supplier_id, feeedback_id, feeedback_answer__text):
        """Отправляем ответ на отзыв"""
        pass


if __name__ == '__main__':
    sellertoken = 'Au7n8BPw0O7ADPCM2MEMQh1PfoKMeTuH7CT-Pnn-_eIHretpsewN14c9_5RyptC0DYc7ttIvfxBTYkcDfzyhNoe2Vq_haFr4MksJ8LKogBwrtA'
    supplier_id = '727553e6-1c20-45af-8f93-031dac28cb1e'
    passporttoken = "Au7n8BOGjdrADIbh7cEMN9Jg-tEZM8Bbj9kYpX6DKnsvEs1Pe-7kEtmWGoxMnRD4DMDpEAQDRsCMv8Lbzw4BPBsnOXsEG4I"
    pass
    # x = WBManager()
    # # phone = input('Введите номер телефона: ')
    # # token = asyncio.run(x.send_phone_number('+79185263659'))
    # #
    # # if token:
    # #     code = input('Введите код из смс: ')
    # #     x.send_sms_code(code, token)
    #
    # sellertoken = 'Au7n8BPw0O7ADPCM2MEMQh1PfoKMeTuH7CT-Pnn-_eIHretpsewN14c9_5RyptC0DYc7ttIvfxBTYkcDfzyhNoe2Vq_haFr4MksJ8LKogBwrtA'
    # # sellertoken = "Au7n8BPui9rADO7Hw8EMQj2TQCao09fPzdscqZ0km5PaI4NCIbd8wkWFn8glvV59q1UyMMwQxrNRX5NgO4BMSVhU5pFP-o7PIKqKBWsOkEQWqw"
    # asyncio.run(x.introspect_seller_token(sellertoken))
    # time.sleep(3)
    #
    # # passporttoken = asyncio.run(x.get_passport_token(sellertoken))
    # # passporttoken = 'Au7n8BP6lO7ADProgcIMN9tYzXtg402VC7QJHqRHhlyKVNgbEQK4vHKusWt6kel34jbfnMCl1bcvVtoqJLH2gBzesDWFNmo'
    # # passporttoken = "Au7n8BOGjdrADIbh7cEMN9Jg-tEZM8Bbj9kYpX6DKnsvEs1Pe-7kEtmWGoxMnRD4DMDpEAQDRsCMv8Lbzw4BPBsnOXsEG4I"
    # # time.sleep(3)
    #
    # # sellertoken = asyncio.run(x.get_seller_token_from_passport_token(passporttoken))
    # # sellertoken = "Au7n8BOUl-7ADJTT18EMQgTZkN0lP-BLm_MVsvhujuQQkpT41iycAV0IZrDUPGOFPJT55WyBnhs0pA9x5f1yyZ3El60kPMmEZ7RYFD9PjsICqw"
    # # sellertoken = "Au7n8BO2mO7ADLbU18EMQpSMCDqTi7WKyw9DLI58MDENtG0V2X5YyoKZ7xkAn_9fpvjFTKrxW3pG_pFtgZ78kiCwTE4H4Rfwpbi1o1X8VhT-7Q"
    # # time.sleep(3)
    # #
    # # wb_token = 'Au7n8BOIv9nADIj7wsEMQrylqaOhAIVlDfC7kuPYvdgyW7WpQBo2B9uAldcY38zb_KZyXk-mAIxw1gjPY8v7TGounFEyRyG1C4Bgm3TGdEtCaQ'
    # suppliers = asyncio.run(x.get_suppliers(sellertoken))
    # time.sleep(3)
    # for supplier_id, supplier_name in suppliers.items():
    #     asyncio.run(x.get_feedback_list(sellertoken, {supplier_id: supplier_name}))
    #     time.sleep(3)


    # for suppl in ['727553e6-1c20-45af-8f93-031dac28cb1e', 'b541a87c-d482-4161-9f30-5edc1fded445']:
