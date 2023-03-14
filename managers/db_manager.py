import functools
from datetime import datetime
from types import FunctionType
from typing import Any, Callable
from aiogram.types import Message, CallbackQuery
from database.db_utils import Tables, db
from config import ADMINS, TECH_ADMINS

"""Все таблицы создаются тут - потому, что таблицы должны создаваться раньше чем экземпляр класса DBManager, иначе 
будут ошибки при создании экземпляров классов кнопок и сообщений"""
db.create_tables(Tables.all_tables())


class DBManager:
    """ Класс Singleton надстройка над ORM "peewee" для соблюдения принципа DRY и вынесения логики сохранения данных """
    dbase = db
    tables = Tables

    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, logger):
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '
        self.decorate_methods()

    @staticmethod
    def db_connector(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(*args, **kwargs) -> Any:
            with DBManager.dbase:
                result = method(*args, **kwargs)
            return result
        return wrapper

    @classmethod
    def decorate_methods(cls):
        for attr_name in cls.__dict__:
            if not attr_name.startswith('__') and attr_name not in ['db_connector', 'decorate_methods']:
                method = cls.__getattribute__(cls, attr_name)
                if type(method) is FunctionType:
                    setattr(cls, attr_name, cls.db_connector(method))

    # Таблицы должны создаваться раньше иначе будут ошибки при создании кнопок и сообщений
    # def create_tables(self):
    #     self.dbase.create_tables(self.tables.all_tables())
    #     self.logger.debug(self.sign + f'OK -> create tables:{self.tables.all_tables()} in DB')

    def get_all_messages(self):
        result = self.tables.messages.select()
        self.logger.debug(
            self.sign + f'OK -> selected all messages from tables: {self.tables.messages} in DB')
        return result

    def reload_table_messages(self, data):
        list_models = []
        for message in data:
            for key1, value in message.items():
                list_models.append(self.tables.messages(callback_data=key1, **value))

        self.tables.messages.truncate_table()
        self.tables.messages.bulk_create(list_models)

    def get_or_create_user(self, update: Message | CallbackQuery) -> tuple:
        admin = True if update.from_user.id in set(tuple(map(
            int, ADMINS)) if ADMINS else tuple() + tuple(map(int, TECH_ADMINS)) if TECH_ADMINS else tuple()) else False

        with self.dbase:
            user, fact_create = self.tables.users.get_or_create(user_id=update.from_user.id)
            if fact_create:
                self.tables.wildberries.get_or_create(user_id=int(update.from_user.id))
                user.user_id = int(update.from_user.id)
                user.username = update.from_user.username,
                user.first_name = update.from_user.first_name,
                user.last_name = update.from_user.last_name,
                user.position = "admin" if admin else "user",
                user.password = "admin" if admin else None
                user.save()

        text = 'created new user in' if fact_create else 'get user from'
        self.logger.debug(
            self.sign + f'OK -> {text} DB -> user_id:{user.user_id}, username: {user.username}')
        return user

    def get_all_users(self, id_only: bool = False, not_ban: bool = False) -> tuple:
        if not_ban and id_only:
            result = tuple(self.tables.users.select(
                self.tables.users.user_id).where(self.tables.users.ban_from_user == 0))
            self.logger.debug(self.sign + f'OK -> selected all users_id WHERE ban != ban from DB')

        elif id_only:
            result = tuple(self.tables.users.select(self.tables.users.user_id))
            self.logger.debug(self.sign + f'OK -> selected all users_id from DB')

        else:
            result = self.tables.users.select()
            self.logger.debug(self.sign + f'OK -> selected all users fields from DB')

        print('ХОРОШО' if isinstance(result, tuple) else 'ПЛОХО', self.sign+'!!!get_all_users_id:!!!', result, type(result))

        return result

    def update_user_balance(self, user_id: str, up_balance: str | None = None,
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
        self.logger.debug(self.sign + f'OK -> update user balance from DB')
        return True, user.balance, user.username

    def update_user_access(self, user_id: str, block: bool = False) -> bool | tuple:
        user = self.tables.users.get_or_none(user_id=user_id)
        if not user:
            return False
        if block:
            user.access = 'block'
        else:
            user.access = 'allowed'
        user.save()
        self.logger.debug(self.sign + f'OK -> update user access {"BLOCK" if block else "ALLOWED"} from DB')
        return True, user.username

    def update_ban_from_user(self, user_id: str, ban_from_user: bool = False) -> bool | tuple:
        user: Tables.users = self.tables.users.get_or_none(user_id=user_id)
        if not user:
            return False
        user.ban_from_user = ban_from_user
        user.save()
        self.logger.debug(self.sign + f'OK -> update user ban_from_user: {ban_from_user} in DB')

        return True, user.username

    def count_users(self, all_users: bool = False, register: bool = False,  date: datetime | None = None) -> str:
        if all_users:
            nums = self.tables.users.select().count()
            self.logger.debug(self.sign + f'OK -> COUNT all users {nums}')

        elif register:
            nums = self.tables.users.select().wheere(self.tables.users.date_join == date).count()
            self.logger.debug(self.sign + f'OK -> COUNT {nums} users WHERE date_join == date: {date}')

        else:
            # nums = self.tables.users.select("SELECT Count() FROM users WHERE date_last_request >= ?", (date,))
            nums = self.tables.users.select().where(self.tables.users.date_last_request >= date).count()
            self.logger.debug(self.sign + f'OK -> COUNT {nums} users WHERE date_last_request == date: {date}')

        print('ХОРОШО' if isinstance(nums, str) else 'ПЛОХО', self.sign+'!!!count_users:!!!', nums, type(nums))
        return nums

    def select_all_contacts_users(self, update: Message | CallbackQuery = None) -> tuple:
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

        print('ХОРОШО' if isinstance(users, tuple) else 'ПЛОХО', self.sign+'!!!select_all_contacts_users:!!!', users, type(users))
        return users

    def select_password(self, user_id: int) -> str:
        user = self.tables.users.select(self.tables.users.password).where(self.tables.users.user_id == user_id).get()
        self.logger.debug(self.sign + f'OK -> SELECT password {user.password}')

        print('ХОРОШО' if isinstance(user.password, str) else 'ПЛОХО', self.sign+'!!!select_password:!!!', user.password, type(user.password))
        return user.password

    def update_last_request_data(self, user_id: str, text_last_request: str) -> bool | None:
        user: Tables.users = self.tables.users.get_or_none(user_id=user_id)
        if not user:
            return False
        user.date_last_request = datetime.now()
        user.num_requests += 1
        user.text_last_request = text_last_request
        user.save()
        self.logger.debug(self.sign + f'OK -> update last_request user in DB user_id:{user_id} '
                                      f'last_request_data: {text_last_request}')

    """Ниже методы работы с WBManager"""
    def save_phone_number_and_sms_token(self, phone_number, sms_token, user_id):
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            wb_user.phone_number = phone_number
            wb_user.sms_token = sms_token
            wb_user.save()

    def save_seller_token(self, seller_token, user_id):
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            wb_user.seller_token = seller_token
            wb_user.save()

    def save_passport_token(self, passport_token, user_id):
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            wb_user.passport_token = passport_token
            wb_user.save()

    def save_wb_user_id(self, wb_user_id, user_id):
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            if not wb_user.WB_user_id or wb_user.WB_user_id != wb_user_id:
                wb_user.WB_user_id = wb_user_id
                wb_user.save()

    def save_suppliers(self, suppliers: dict, user_id):
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            wb_user.suppliers = suppliers
            wb_user.save()

        # for s_name, s_id in suppliers.items():
        #     supplier = self.tables.suppliers.get_or_create(x_supplier_id=s_id, user_id=user_id, name=s_name,
        #                                                    callback=f'Shop{s_id}')
            # supplier.name = s_name
            # supplier.save()

    # def get_suppliers(self):
    #     TODO
        # pass

    def save_unanswered_feedbacks(self, unanswered_feedbacks: dict, user_id):
        wb_user = self.tables.wildberries.get_or_none(user_id=user_id)
        if wb_user:
            wb_user.unanswered_feedbacks = {**wb_user.unanswered_feedbacks, **unanswered_feedbacks}
            wb_user.save()