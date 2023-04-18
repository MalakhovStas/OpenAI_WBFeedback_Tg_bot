from datetime import datetime, timedelta
from config import PRODAMUS_PRIV_KEY, LINKTOFORM, CUSTOMER_EMAIL, URL_RETURN, URL_NOTIFICATION, PAYMENTS_PACKAGES
from collections.abc import MutableMapping
from urllib.parse import urlencode


class ProdamusManager:
    """Класс для работы с API платёжной системы Prodamus"""
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, rm, dbase, logger):
        self.rm = rm
        self.dbase = dbase
        self.logger = logger
        self.secret_key = PRODAMUS_PRIV_KEY
        self.linktoform = LINKTOFORM
        self.url_notification = URL_NOTIFICATION
        self.payment_packages = PAYMENTS_PACKAGES
        self.link_expired = None  # Срок действия ссылки на оплату - количество дней int / или None - срок не ограничен
        self.customer_email = CUSTOMER_EMAIL
        self.url_return = URL_RETURN
        # self.sign = self.__class__.__name__ + ': '

    async def __call__(self, user_id, package_name):
        return await self.generate_payment_link(user_id=user_id, package_name=package_name)

    async def generate_payment_link(self, user_id: str | int, package_name: str) -> str:
        order_num = await self.dbase.create_new_payment_order(user_id=user_id)
        link_expired = '' if not self.link_expired else datetime.strftime(
            datetime.now() + timedelta(days=self.link_expired), '%d.%m.%Y %H:%M')
        data = {
            'order_id': order_num,
            'customer_email': self.customer_email,
            'products': [
                {
                    'name': package_name,
                    'price': self.payment_packages.get(package_name).get('price'),
                    'quantity': '1',
                    'paymentMethod': 4,
                    'paymentObject': 4,
                },
            ],
            'do': 'link',
            'urlReturn': self.url_return,
            'urlSuccess': self.url_return,
            'urlNotification': self.url_notification,
            'npd_income_type': 'FROM_INDIVIDUAL',
            'link_expired': link_expired,
            'paid_content': 'Оплата прошла успешно, благодарим за пользование нашими услугами',
            '_param_user_id': user_id
        }

        data['signature'] = await self.sign(data, self.secret_key)
        link = self.linktoform + '?' + urlencode(await self.http_build_query(data))

        payment_link = (await self.rm(url=link, use_proxi=False)).get('response')
        await self.dbase.update_payment_order(order_num=order_num, payment_link=payment_link, payment_link_data=data)
        return payment_link

    async def sign(self, data, secret_key):
        import hashlib
        import hmac
        import json

        # переводим все значения data в string c помощью кастомной функции deep_int_to_string (см ниже)
        await self.deep_int_to_string(data)

        # переводим data в JSON, с сортировкой ключей в алфавитном порядке, без пробелов и экранируем бэкслеши
        data_json = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(',', ':')).replace("/", "\\/")

        # создаем подпись с помощью библиотеки hmac и возвращаем ее
        return hmac.new(secret_key.encode('utf8'), data_json.encode('utf8'), hashlib.sha256).hexdigest()

    async def deep_int_to_string(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, MutableMapping):
                await self.deep_int_to_string(value)
            elif isinstance(value, list) or isinstance(value, tuple):
                for k, v in enumerate(value):
                    await self.deep_int_to_string({str(k): v})
            else:
                dictionary[key] = str(value)

    async def http_build_query(self, dictionary, parent_key=False):
        items = []
        for key, value in dictionary.items():
            new_key = str(parent_key) + '[' + key + ']' if parent_key else key
            if isinstance(value, MutableMapping):
                items.extend((await self.http_build_query(value, new_key)).items())
            elif isinstance(value, list) or isinstance(value, tuple):
                for k, v in enumerate(value):
                    items.extend((await self.http_build_query({str(k): v}, new_key)).items())
            else:
                items.append((new_key, value))
        return dict(items)

