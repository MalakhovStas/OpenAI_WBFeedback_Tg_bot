import functools
from datetime import datetime
from types import FunctionType
from typing import Any, Callable

from aiogram.types import Message, CallbackQuery
from loguru import logger

from config import ADMINS, TECH_ADMINS
from database.db_utils import Tables, db

"""Все таблицы создаются тут - потому, что таблицы должны создаваться раньше чем экземпляр класса DBManager, иначе 
будут ошибки при создании экземпляров классов кнопок и сообщений"""
db.create_tables(Tables.all_tables())


class DBManager:
    """ Класс Singleton надстройка над ORM "peewee" для соблюдения принципа DRY и вынесения логики сохранения данных """
    point_db_connection = db
    tables = Tables

    __instance = None
    sign = None
    logger = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.sign = cls.__name__ + ': '
            cls.logger = logger
            cls.decorate_methods()
        return cls.__instance

    def __init__(self):
        pass
        # self.logger = logger
        # sign = __class__.__name__ + ': '
        # self.decorate_methods()

    @staticmethod
    def db_connector(method: Callable) -> Callable:
        @functools.wraps(method)
        async def wrapper(*args, **kwargs) -> Any:
            with DBManager.point_db_connection:
                result = await method(*args, **kwargs)
            return result
        return wrapper

    @classmethod
    def decorate_methods(cls):
        for attr_name in cls.__dict__:
            if not attr_name.startswith('__') and attr_name not in ['db_connector', 'decorate_methods']:
                method = cls.__getattribute__(cls, attr_name)
                if type(method) is FunctionType:
                    cls.logger.debug(cls.sign + f'decorate_methods -> db_connector wrapper -> method: {attr_name}')
                    setattr(cls, attr_name, cls.db_connector(method))

    # Таблицы должны создаваться раньше иначе будут ошибки при создании кнопок и сообщений
    # def create_tables(self):
    #     self.point_db_connection.create_tables(self.tables.all_tables())
    #     self.logger.debug(self.sign + f'OK -> create tables:{self.tables.all_tables()} in DB')

    # async def get_all_messages(self):
    #     result = self.tables.messages.select()
    #     self.logger.debug(
    #         self.sign + f'OK -> selected all messages from tables: {self.tables.messages}')
    #     return result
    #
    # async def reload_table_messages(self, data):
    #     list_models = []
    #     for message in data:
    #         for key1, value in message.items():
    #             list_models.append(self.tables.messages(callback_data=key1, **value))
    #
    #     self.tables.messages.truncate_table()
    #     self.tables.messages.bulk_create(list_models)

    async def get_or_create_user(self, update: Message | CallbackQuery) -> tuple[tuple, bool | int]:
        """ Если user_id не найден в таблице Users -> создаёт новые записи в
            таблицах Users и Wildberries по ключу user_id """
        fact_create_and_num_users = False
        admin = True if update.from_user.id in set(tuple(map(
            int, ADMINS)) if ADMINS else tuple() + tuple(map(int, TECH_ADMINS)) if TECH_ADMINS else tuple()) else False

        with self.point_db_connection:
            user, fact_create = self.tables.users.get_or_create(user_id=update.from_user.id)
            if fact_create:
                self.tables.wildberries.get_or_create(user_id=int(update.from_user.id))
                fact_create_and_num_users = self.tables.users.select().count()
                user.user_id = int(update.from_user.id)
                user.username = update.from_user.username
                user.first_name = update.from_user.first_name
                user.last_name = update.from_user.last_name
                user.position = "admin" if admin else "user"
                user.password = "admin" if admin else None
                user.save()

        text = 'created new user' if fact_create else 'get user'
        self.logger.debug(self.sign + f' {text.upper()}: {user.username=} | {user.user_id=}')
        return user, fact_create_and_num_users

    async def get_all_users(self, id_only: bool = False, not_ban: bool = False) -> tuple:
        if not_ban and id_only:
            result = tuple(self.tables.users.select(
                self.tables.users.user_id).where(self.tables.users.ban_from_user == 0))
            self.logger.debug(self.sign + f'func get_all_users -> selected all users_id WHERE ban != ban '
                                          f'num: {len(result) if result else None}')

        elif id_only:
            result = tuple(self.tables.users.select(self.tables.users.user_id))
            self.logger.debug(self.sign + f'func get_all_users -> selected all users_id '
                                          f'num: {len(result) if result else None}')

        else:
            result = self.tables.users.select()
            self.logger.debug(self.sign + f'func get_all_users -> selected all users fields '
                                          f'num: {len(result) if result else None}')

        return result

    async def update_user_balance(self, user_id: str, up_balance: str | None = None,
                                  down_balance: str | None = None, zero_balance: bool = False) -> tuple | bool:
        user = self.tables.users.get_or_none(user_id=user_id)
        if not user:
            return False

        if up_balance and up_balance.isdigit():
            user.balance += int(up_balance)
        elif down_balance and down_balance.isdigit():
            user.balance -= int(down_balance)
        elif zero_balance:
            user.balance = 0
        else:
            return False, 'bad data'
        user.save()

        if up_balance:
            result = f'up_balance: {up_balance}'
        elif down_balance:
            result = f'down_balance: {down_balance}'
        else:
            result = f'zero_balance: {zero_balance}'

        self.logger.debug(self.sign + f'{user_id=} | {result=} | new {user.balance=}')
        return True, user.balance, user.username

    async def update_user_balance_requests(self, user_id: str | int,
                                           up_balance: str | int | None = None,
                                           down_balance: str | int | None = None,
                                           zero_balance: bool = False) -> tuple | bool:
        user = self.tables.users.get_or_none(user_id=str(user_id))
        if not user:
            return False

        if up_balance and str(up_balance).isdigit():
            user.balance_requests += int(up_balance)
        elif down_balance and str(down_balance).isdigit():
            if user.balance_requests != 0:
                user.balance_requests -= int(down_balance)
            else:
                return False, 'not update user balance_requests=0'
        elif zero_balance:
            user.balance_requests = 0
        else:
            return False, 'bad data'
        user.save()

        if up_balance:
            result = f'up_balance: {up_balance}'
        elif down_balance:
            result = f'down_balance: {down_balance}'
        else:
            result = f'zero_balance: {zero_balance}'

        self.logger.debug(self.sign + f'{user_id=} | {result=} | new {user.balance_requests=}')
        return True, user.balance_requests, user.username

    async def update_user_access(self, user_id: str | int, block: bool = False) -> bool | tuple:
        user = self.tables.users.get_or_none(user_id=user_id)
        if not user:
            return False
        if block:
            user.access = 'block'
        else:
            user.access = 'allowed'
        user.save()
        self.logger.debug(self.sign + f'func update_user_access -> {"BLOCK" if block else "ALLOWED"} '
                                      f'| user_id: {user_id}')
        return True, user.username

    async def update_ban_from_user(self, update, ban_from_user: bool = False) -> bool | tuple:
        user: Tables.users = self.tables.users.get_or_none(user_id=update.from_user.id)
        if not user:
            return False
        user.ban_from_user = ban_from_user
        user.save()
        self.logger.debug(self.sign + f'func update_ban_from_user -> user: {user.username} | '
                                      f'user_id: {update.from_user.id} | ban: {ban_from_user}')
        return True, user.username

    async def count_users(self, all_users: bool = False, register: bool = False,  date: datetime | None = None) -> str:
        if all_users:
            nums = self.tables.users.select().count()
            self.logger.debug(self.sign + f'func count_users -> all users {nums}')

        elif register:
            nums = self.tables.users.select().wheere(self.tables.users.date_join == date).count()
            self.logger.debug(self.sign + f'func count_users -> num users: {nums} WHERE date_join == date: {date}')

        else:
            nums = self.tables.users.select().where(self.tables.users.date_last_request >= date).count()
            self.logger.debug(self.sign + f'func count_users -> num users: {nums} '
                                          f'WHERE date_last_request == date: {date}')

        return nums

    async def select_all_contacts_users(self) -> tuple:
        users = self.tables.users.select(
            self.tables.users.user_id,
            self.tables.users.first_name,
            self.tables.users.username,
            self.tables.users.date_join,
            self.tables.users.date_last_request,
            self.tables.users.text_last_request,
            self.tables.users.num_requests,
            self.tables.users.ban_from_user)

        if not users:
            self.logger.error(self.sign + f'BAD -> NOT users in DB')
        else:
            self.logger.debug(self.sign + f'OK -> SELECT all contacts users -> return -> {len(users)} users contacts')

        return users

    async def select_password(self, user_id: int) -> str:
        user = self.tables.users.select(self.tables.users.password).where(self.tables.users.user_id == user_id).get()
        self.logger.debug(self.sign + f'func select_password password -> len password {len(user.password)}')

        return user.password

    async def update_last_request_data(self, update, text_last_request: str) -> bool | None:
        user = self.tables.users.get_or_none(user_id=update.from_user.id)
        if not user:
            return False

        user.date_last_request = datetime.now()
        user.num_requests += 1
        user.text_last_request = text_last_request
        user.save()
        self.logger.debug(self.sign + f'func update_last_request_data -> user: {update.from_user.username} | '
                                      f'user_id:{update.from_user.id} | '
                                      f'last_request_data: {text_last_request}')

    """ Методы работы с таблицей wildberries"""
    async def select_all_wb_users(self):
        wb_users = list(self.tables.wildberries.select())
        return wb_users

    async def wb_user_get_or_none(self, user_id: int) -> Tables.wildberries | None:
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        self.logger.info(self.sign + f' wb_user_get_or_none {wb_user=}')
        return wb_user

    async def update_wb_user(self, user_id: int, update_data: dict) -> Tables.wildberries | None:
        wb_user = await self.wb_user_get_or_none(user_id=user_id)

        if not self.tables.wildberries.update(**update_data).where(
                self.tables.wildberries.user_id == user_id).execute():
            self.logger.error(self.sign + f'update_wb_user ERROR -> {user_id=} -> '
                                          f'NOT UPDATE: {wb_user.__data__=} | {update_data=}')

        wb_user = await self.wb_user_get_or_none(user_id=user_id)
        self.logger.debug(self.sign + f'update_wb_user -> Telegram user_id: {wb_user.user_id} | '
                                      f'{wb_user.WB_user_id=} | {update_data.keys()=}')

        return wb_user

    """Методы которые использует WBManager"""
    async def save_phone_number_and_sms_token(self, phone_number, sms_token, user_id):
        if wb_user := self.tables.wildberries.get_or_none(user_id=user_id):
            wb_user.phone = phone_number
            wb_user.sms_token = sms_token
            wb_user.save()

    async def save_seller_token(self, seller_token, user_id):
        self.logger.info(self.sign + f'save sellerToken: {seller_token}')

        if wb_user := self.tables.wildberries.get_or_none(user_id=user_id):
            wb_user.sellerToken = seller_token
            wb_user.save()

    async def save_passport_token(self, passport_token, user_id):
        self.logger.info(self.sign + f'save passportToken: {passport_token}')
        if wb_user := self.tables.wildberries.get_or_none(user_id=user_id):
            wb_user.passportToken = passport_token
            wb_user.save()

    async def save_wb_user_id(self, wb_user_id, user_id):
        self.logger.debug(self.sign + f'check {wb_user_id=} | {user_id=}')
        if wb_user := self.tables.wildberries.get_or_none(user_id=user_id):
            if not wb_user.WB_user_id or wb_user.WB_user_id != wb_user_id:
                wb_user.WB_user_id = wb_user_id
                wb_user.save()
                self.logger.info(self.sign + f'save wb_user_id: {wb_user_id}')

    async def save_suppliers(self, suppliers: dict, user_id):
        self.logger.info(self.sign + f'save suppliers: {suppliers}')
        if wb_user := self.tables.wildberries.get_or_none(user_id=user_id):
            wb_user.suppliers.update(suppliers)
            wb_user.save()

    async def save_unanswered_feedbacks(self, unanswered_feedbacks: dict, user_id):
        """ Сохранение отзывов в БД -> wildberries -> unanswered_feedbacks """
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            feedback_in_db = wb_user.unanswered_feedbacks
            if feedback_in_db and isinstance(feedback_in_db, dict):
                wb_user.unanswered_feedbacks = {**feedback_in_db, **unanswered_feedbacks}
                self.logger.info(self.sign + f'update unanswered_feedbacks: {len(feedback_in_db)=} | '
                                             f'{len(unanswered_feedbacks)=} total: {len(wb_user.unanswered_feedbacks)}')

            else:
                wb_user.unanswered_feedbacks = unanswered_feedbacks
                self.logger.info(self.sign + f'save num unanswered_feedbacks: {len(unanswered_feedbacks)} '
                                             f'this all unans_feeds in DB')
            wb_user.save()

    """ Методы работы с таблицей payments"""
    async def create_new_payment_order(self, user_id):
        order_num = self.tables.payments.insert(user_id=user_id).execute()
        self.logger.info(self.sign + f'create new payment_order: {order_num=}')
        return order_num

    async def update_payment_order(self, order_num, payment_link: str | None = None,
                                   payment_link_data: dict | None = None):
        if order := self.tables.payments.get_or_none(id=order_num):
            if payment_link:
                order.payment_link = payment_link
            if payment_link_data:
                order.payment_link_data = payment_link_data
            order.save()
            self.logger.info(self.sign + f'update payment_order: {order.__dict__.get("__data__")}')
            return order

    async def select_all_payment_orders_user(self, user_id):
        payment_orders_user = list(self.tables.payments.select().where(self.tables.payments.user_id == user_id))
        return payment_orders_user
