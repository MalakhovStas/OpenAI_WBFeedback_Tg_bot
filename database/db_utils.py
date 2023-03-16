import functools
import json
from datetime import datetime

from peewee import *
from peewee import ModelBase

from config import DATABASE_CONFIG
# from playhouse.sqlite_ext import JSONField
from playhouse.sqlite_ext import JSONField, SqliteDatabase

my_json_dumps = functools.partial(json.dumps, ensure_ascii=False)
databases = {
    'sqlite': SqliteDatabase,
    'postgres': PostgresqlDatabase,
    'mysql': MySQLDatabase
}

db: SqliteDatabase | PostgresqlDatabase | MySQLDatabase = databases[DATABASE_CONFIG[0]](**DATABASE_CONFIG[1])


class Button(Model):
    button_id = IntegerField(primary_key=True)
    parent_id = IntegerField(null=True)
    name = CharField(null=True)
    callback = CharField(null=True)
    reply_text = TextField(null=True)
    url = CharField(max_length=511, null=True)
    next_state = CharField(null=True)
    children = JSONField(null=True)  # Разобраться с JSON других моделей
    messages = JSONField(null=True)  # Разобраться с JSON других моделей

    class Meta:
        database = db
        order_by = 'parent_id'
        db_table = 'buttons'


class Message(Model):
    button_id = ForeignKeyField(Button, related_name='messages', to_field=Button.button_id,
                                on_delete='CASCADE', on_update='CASCADE', null=True, unique=False)
    state_or_key = CharField(null=True)
    reply_text = TextField(null=True)
    next_state = CharField(null=True)
    children_buttons = JSONField(null=True)  # Разобраться с JSON других моделей

    class Meta:
        database = db
        order_by = 'button_id'
        db_table = 'messages_button'


class Users(Model):
    """ Модель одноименной таблицы в базе данных """
    user_id = IntegerField(primary_key=True, unique=True)
    username = CharField(null=True)
    first_name = CharField(null=True)
    last_name = CharField(null=True)

    referer_id = IntegerField(null=True)  # Телеграм id пользователя по чьей ссылке пришел этот пользователь
    date_join = DateTimeField(default=datetime.now(), null=False)  # Два поля для одного и того-же
    # registered = DateTimeField(default=datetime.now(), null=False)  # Два поля для одного и того-же

    access = CharField(default='allowed', null=False)  # Режим доступа к боту
    start_time_limited = IntegerField(null=True)  # Время начала блокировки пользователя используется в middleware
    position = CharField(null=False, default='user')  # Позиция - user | admin
    password = CharField(null=True)  # Пароль обязателен для admin

    date_last_request = DateTimeField(default=datetime.now(), null=False)  # Дата последнего запроса
    text_last_request = CharField(null=False, default='first start command')  # Текст последнего запроса
    num_requests = IntegerField(null=False, default=1)  # Общее кол-во запросов
    ban_from_user = BooleanField(null=False, default=False)  # Забанил ли пользователь бота

    balance_requests = IntegerField(null=False, default=0)  # Баланс кол-ва запросов разрешенных
    balance = DecimalField(max_digits=10, decimal_places=2, default=0, null=False)  # Финансовый баланс
    subscription = DateTimeField(null=True)  # Подписка до этой даты

    class Meta:
        database = db
        order_by = 'date_join'
        db_table = 'users'


class Wildberries(Model):
    user_id = ForeignKeyField(Users, to_field='user_id', related_name='wildberries', on_delete='CASCADE')
    WB_user_id = IntegerField(null=True)
    phone = CharField(max_length=20, null=True)
    sms_token = CharField(null=True)
    sellerToken = CharField(null=True)
    passportToken = CharField(null=True)

    suppliers = JSONField(null=False, default=dict())
    unanswered_feedbacks = JSONField(null=False, default=dict())
    ignored_feedbacks = JSONField(null=False, default=dict())

    signature_to_answer = CharField(null=True)

    notification_times = CharField(null=False, default='around_the_clock')
    timezone_notification_times = CharField(null=False, default='Москва (UTC +2)')

    automatic_replies_notifications = BooleanField(null=False, default=True)
    answer_mode = JSONField(null=False, default={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0})

    class Meta:
        database = db
        order_by = 'phone'
        db_table = 'wildberries'


# class Supplier(Model):
#     user_id = ForeignKeyField(Users, to_field='user_id', related_name='suppliers', on_delete='CASCADE')
#     x_supplier_id = CharField(primary_key=True, unique=True)
#     name = CharField()
#     callback = CharField(null=True)
#
#     class Meta:
#         database = db
#         order_by = 'user_id'
#         db_table = 'suppliers'
#
#
# class Feedback(Model):
#     user_id = ForeignKeyField(Users, to_field='user_id', related_name='suppliers', on_delete='CASCADE')
#     x_supplier_id = ForeignKeyField(Supplier, to_field='x_supplier_id', related_name='feedbacks', on_delete='CASCADE')
#     feedback_id = CharField(primary_key=True, unique=True)
#     generate_answer = CharField(null=True)
#     ignore_feedback = BooleanField(null=False, default=False)
#
#     class Meta:
#         database = db
#         order_by = 'user_id'
#         db_table = 'feedbacks'


class Tables:
    users = Users
    buttons = Button
    messages = Message
    wildberries = Wildberries
    # suppliers = Supplier
    # feedbacks = Feedback

    @classmethod
    def all_tables(cls):
        return [value for value in cls.__dict__.values() if isinstance(value, ModelBase)]