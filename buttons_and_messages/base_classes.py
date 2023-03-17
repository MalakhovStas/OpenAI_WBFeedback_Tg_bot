import asyncio
import re
from abc import ABC
from types import FunctionType
from typing import Any
from loguru import logger
from database.db_utils import db, Tables


class Base(ABC):

    dbase = db
    tables = Tables

    ai = None  # Добавляется в loader.py
    bot = None  # Добавляется в loader.py
    wb_api = None  # Добавляется в loader.py
    wb_parsing = None  # Добавляется в loader.py
    logger = logger  # Добавляется в loader.py

    # exception_controller = None  # Добавляется в loader.py

    default_bad_text = 'нет данных'
    default_incorrect_data_input_text = 'Введены некорректные данные, попробуйте немного позже'
    default_generate_answer = '✍ Генерирую ответ, немного подождите пожалуйста ...'
    default_download_information = '🌐 Загружаю информацию, немного подождите пожалуйста ...'

    message_store = dict()
    button_store = dict()
    supplier_collection = dict()
    feedback_collection = dict()

    def log(self, message):
        # self.logger.debug(f'Class: {self.__class__.__name__}:' + message)
        pass

    def _set_reply_text(self) -> str | None:
        """Установка текста ответа """
        reply_text = 'Default: reply_text not set -> override method _set_reply_text ' \
                     'in class' + self.__class__.__name__
        return reply_text

    def _set_next_state(self) -> str | None:
        """Установка следующего состояния """
        return None

    def _set_children(self) -> list:
        """ Установка дочерних кнопок """
        return list()

    @classmethod
    async def get_many_buttons_from_any_collections(cls, get_buttons_list: list | tuple) -> Any | None:
        # cls.logger.debug(f'Base: get_many_buttons_from_any_collections -> get_buttons_list: {get_buttons_list}')
        result_buttons_list = list()

        if get_buttons_list:
            for button_name in get_buttons_list:
                if result_button := await cls.button_search_and_action_any_collections(
                        button_name=button_name, action='get'):
                    result_buttons_list.append(result_button)

        # cls.logger.debug(f'Base: get_many_buttons_from_any_collections -> {"OK" if result_buttons_list else "BAD"} '
        #                  f'get_buttons_list: {get_buttons_list}, return result: {result_buttons_list}')
        return result_buttons_list

    @classmethod
    async def button_search_and_action_any_collections(cls, action: str, button_name: str | None = None,
                                                       instance_button: Any | None = None) -> Any | None:
        # cls.logger.debug(f'Base: action: {action.upper()}, button_name: {button_name}, instance_button: {instance_button}')

        if not button_name and not instance_button:
            return None

        if instance_button:
            button_name = instance_button.__class__.__name__

        if button_name.startswith('Supplier'):
            collection = cls.supplier_collection
            collection_name = 'supplier_collection'
        elif button_name.startswith('Feedback'):
            collection = cls.feedback_collection
            collection_name = 'feedback_collection'
        else:
            collection = cls.button_store
            collection_name = 'button_store'

        # cls.logger.debug(f'Base: set collection:{collection_name.upper()} for {action.upper()} button_name: {button_name}')

        if instance_button and action == 'add':
            collection.update({button_name: instance_button})
            button = instance_button
        elif action == 'get':
            button = collection.get(button_name)
        elif action == 'pop':
            button = collection.pop(button_name, None)
        else:
            button = None

        # cls.logger.debug(f'Base: result:{"OK" if button else "BAD"} -> return button: {button}')
        return button

    @staticmethod
    async def change_name_button(button, num):
        i_was = None
        res_re = re.search(r'< \d+ >', button.name)
        if res_re:
            i_was = res_re.group(0)
        was = i_was if i_was else '< 0 >'

        will_be = f"< {num} >"
        button.name = button.name.replace(was, will_be)
        return button

    # @classmethod
    # def decorate_methods_for_exception_control(cls):
    #     """Декорирует методы _set_answer_logic во всех классах для контроля исключений вызов этого метода в __init__
    #     базовых классов"""
    #     for attr_name in cls.__dict__:
    #         if not attr_name.startswith('__') and attr_name == '_set_answer_logic':
    #             method = cls.__getattribute__(cls, attr_name)
    #             if type(method) is FunctionType:
    #                 setattr(cls, attr_name, cls.exception_controller(method))


class BaseMessage(Base):
    """ Логика - которая будет прописана в дочерних классах выполниться только один раз при старте программы
    динамическая логика должна быть прописана в методе _set_answer_logic. Каждая кнопка при создании автоматически
    добавляется в коллекцию на основе префикса"""

    __instance = None
    base_sign = 'BaseMessage: '

    __slots__ = ('button_id', 'state_or_key', 'reply_text',
                 'children_buttons', 'next_state', 'parent_name', 'class_name')

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, button: Any | int | None = None, state_or_key: str | None = None, reply_text: str | None = None,
                 children_buttons: list | None = None, parent_name: str | None = None):

        if self.__class__.__name__ != BaseMessage.__name__:
            self.class_name = self.__class__.__name__
            self.button_id = button.button_id if (button and isinstance(button, BaseButton)) else button
            self.parent_name = parent_name
            self.state_or_key = self._set_state_or_key() if not state_or_key else state_or_key
            self.reply_text = self._set_reply_text() if not reply_text else reply_text
            self.children_buttons = self._set_children() if not children_buttons else children_buttons
            self.next_state = self._set_next_state()
            self._save_message()
            self.message_store.setdefault(self.state_or_key, self)

    def __str__(self):
        return f'message: {self.__class__.__name__} button_id: {self.button_id}, state_or_key: {self.state_or_key}, ' \
               f'reply_text: {self.reply_text[:15]}..., ' \
               f'children: {[f"< {child.__class__.__name__}: {child.name} >" for child in self.children_buttons]}'

    def _set_state_or_key(self) -> str:
        """ Установка состояния или ключа по которому вызывается дочерний класс для обработки входящего сообщения """
        reply_text = 'Default: state_or_key not set -> override method _set_state_or_key ' \
                     'in class' + self.__class__.__name__
        return reply_text

    def _save_message(self) -> None:
        """ Сохраняет данные сообщения в БД возможно их изменение при __call__ экземпляра класса """
        with self.dbase:
            message, fact_create = self.tables.messages.get_or_create(button_id=self.button_id)
            if message:
                message.state_or_key = self.state_or_key
                message.reply_text = self.reply_text
                message.children_buttons = [child.button_id for child in self.children_buttons]
                if fact_create:
                    self.logger.debug(self.base_sign + f'create new object message: {self.class_name} in DB')
                else:
                    self.logger.debug(self.base_sign + f'update object message: {self.class_name} in DB')


class BaseButton(Base):
    """ Логика - которая будет прописана в дочерних классах выполниться только один раз при старте программы
    динамическая логика должна быть прописана в методе _set_answer_logic. Каждая кнопка при создании автоматически
    добавляется в коллекцию на основе префикса"""

    __instance = None
    __buttons_id = [0, ]
    base_sign = 'BaseButton: '

    __slots__ = ('button_id', 'name', 'url', 'callback', 'parent_id', 'reply_text', 'next_state',
                 'children_buttons', 'children_messages', 'any_data', 'parent_name', 'class_name')

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, name: str | None = None, callback: str | None = None, new=True,
                 parent_id: int | None = None, parent_name: str | None = None, parent_callback: str | None = None,
                 reply_text: str | None = None, children: list | None = None, messages: dict | None = None,
                 any_data: dict | None = None, next_state: str | None = None):

        if new and self.__class__.__name__ != BaseButton.__name__:
            self.class_name = self.__class__.__name__
            self.button_id = self.__set_button_id()
            self.name = self._set_name() if not name else name
            self.url = self._set_url()
            self.callback = self._set_callback() if not callback else callback
            self.parent_name = parent_name

            self.parent_id = self._get_button_id(button_id=parent_id, name=parent_name, callback=parent_callback)
            self.reply_text = self._set_reply_text() if not reply_text else reply_text
            self.next_state = self._set_next_state() if not next_state else next_state
            self.any_data = any_data

            self.__save_button()
            self.children_buttons = self._set_children() if not children else children
            self.children_messages = self._set_messages() if not messages else messages
            self.__update_children_and_messages()

            self.message_store.update(self.children_messages)

            if self.__class__.__name__.startswith('Supplier'):
                self.supplier_collection[self.__class__.__name__] = self
            elif self.__class__.__name__.startswith('Feedback'):
                self.feedback_collection[self.__class__.__name__] = self
            else:
                self.button_store[self.__class__.__name__] = self

    def __str__(self):
        return f'button: {self.__class__.__name__} button_id: {self.button_id}, name: {self.name}, callback: ' \
               f'{self.callback}, parent_id: {self.parent_id}, reply_text: {self.reply_text[:15]}..., ' \
               f'children: {[f"< {child.__class__.__name__}: {child.name} >" for child in self.children_buttons]}, ' \
               f'messages: {[f"< {message.__class__.__name__}: {message.state_or_key} >" for message in self.children_messages.values()]}'

    def __set_button_id(self) -> int:
        sorted(self.__buttons_id)
        button_id = self.__buttons_id[-1] + 1
        self.__buttons_id.append(button_id)
        return button_id

    def __save_button(self) -> None:
        """Вызывается один раз при создании singleton экземпляра класса"""
        with self.dbase:
            button, fact_create = self.tables.buttons.get_or_create(button_id=self.button_id)
            if button:
                button.parent_id = self.parent_id
                button.name = self.name
                button.callback = self.callback
                button.reply_text = self.reply_text
                button.save()
                if fact_create:
                    self.logger.debug(self.base_sign + f'create new object button: {self.class_name} in DB')
                else:
                    self.logger.debug(self.base_sign + f'update object button: {self.class_name} in DB')

    def __update_children_and_messages(self) -> None:
        """Вызывается один раз при создании singleton экземпляра класса"""
        with self.dbase:
            if button := self.tables.buttons.get_or_none(button_id=self.button_id):
                button.children = [child.button_id for child in self.children_buttons]
                button.messages = [child.state_or_key for child in self.children_messages.values()]
                button.save()
                self.logger.debug(self.base_sign + f'update lists children objects in object button: {self.class_name} in DB')

    def _set_name(self) -> str:
        name = 'Button:' + self.class_name
        return name

    def _set_callback(self) -> str | None:
        if self.url:
            return None
        return self.class_name

    def _set_url(self) -> str | None:
        return None

    def _set_messages(self) -> dict:
        return dict()

    def _get_button_id(
            self, button_id: int | None = None, name: str | None = None, callback: str | None = None) -> int | None:
        if name and callback:
            button = self.tables.buttons.get_or_none(
                self.tables.buttons.name == name, self.tables.buttons.callback == callback)
        elif button_id:
            button = self.tables.buttons.get_or_none(self.tables.buttons.button_id == button_id)
        elif name:
            button = self.tables.buttons.get_or_none(self.tables.buttons.name == name)
        elif callback:
            button = self.tables.buttons.get_or_none(self.tables.buttons.callback == callback)
        else:
            button = None
        button = button.button_id if button else None
        return button

    async def get_parent(self):
        return await self.button_search_and_action_any_collections(action='get', button_name=self.parent_name)
