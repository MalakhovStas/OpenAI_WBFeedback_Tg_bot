import asyncio
import itertools
import re
from abc import ABC
from typing import Any

from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from config import BOT_NIKNAME, NUM_FEED_BUTTONS
# from database.db_utils import db, Tables
from database.db_utils import Tables
from managers.db_manager import DBManager
from utils.states import FSMPersonalCabinetStates, FSMUtilsStates
from utils import misc_utils

class Base(ABC):

    # dbase = db
    tables = Tables
    dbase = DBManager()  # TODO попробовать добавить через loader.py
    # dbase = None

    ai = None  # Добавляется в loader.py
    bot = None  # Добавляется в loader.py
    wb_api = None  # Добавляется в loader.py
    wb_parsing = None  # Добавляется в loader.py
    m_utils = misc_utils
    logger = logger
    # exception_controller = None  # Добавляется в loader.py

    default_bad_text = 'нет данных'
    default_incorrect_data_input_text = 'Введены некорректные данные, попробуйте немного позже'
    default_generate_answer = '✍ Генерирую ответ, немного подождите пожалуйста ...'
    default_download_information = '🌐 Загружаю информацию, немного подождите пожалуйста ...'

    message_store = dict()
    button_store = dict()
    supplier_collection = dict()
    feedback_collection = dict()
    aufm_feeds_collection = dict()

    def log(self, message, level: str | None = None):
        text = f'class: {self.__class__.__name__}: ' + message

        if level.lower() == 'info':
            self.logger.info(text)

        elif level.lower() == 'warning':
            self.logger.warning(text)

        elif level.lower() == 'error':
            self.logger.error(text)

        else:
            self.logger.debug(text)

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
        cls.logger.debug(f'Base: get_many_buttons_from_any_collections -> get_buttons_list: {get_buttons_list}')
        result_buttons_list = list()

        if get_buttons_list:
            for button_name in get_buttons_list:
                if result_button := await cls.button_search_and_action_any_collections(
                        button_name=button_name, action='get'):
                    result_buttons_list.append(result_button)

        cls.logger.debug(f'Base: get_many_buttons_from_any_collections -> {"OK" if result_buttons_list else "BAD"} '
                         f'get_buttons_list: {get_buttons_list}, return result: {result_buttons_list}')
        return result_buttons_list

    @classmethod
    async def button_search_and_action_any_collections(cls, action: str, button_name: str | None = None,
                                                       instance_button: Any | None = None) -> Any | None:
        cls.logger.debug(f'Base: action: {action.upper()} | button_name: {button_name} | '
                         f'instance_button: {instance_button} | func: button_search_and_action_any_collections')

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

        cls.logger.debug(f'Base: set collection:{collection_name.upper()} for {action.upper()} | '
                         f'button_name: {button_name} | func: button_search_and_action_any_collections')

        if instance_button and action == 'add':
            collection.update({button_name: instance_button})
            button = instance_button
        elif action == 'get':
            button = collection.get(button_name)
        elif action == 'pop':
            button = collection.pop(button_name, None)
        else:
            button = None

        cls.logger.debug(f'Base: result:{"OK" if button else "BAD"} -> return {button=} '
                         f'| func: button_search_and_action_any_collections')
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

    __slots__ = ('button_id', 'state_or_key', 'reply_text', 'children_buttons', 'next_state',
                 'parent_name', 'parent_button', 'class_name')

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, button: Any | int | None = None, state_or_key: str | None = None, reply_text: str | None = None,
                 children_buttons: list | None = None, parent_name: str | None = None, parent_button: Any | None = None):

        if self.__class__.__name__ != BaseMessage.__name__:
            self.class_name = self.__class__.__name__
            self.button_id = button.button_id if (button and isinstance(button, BaseButton)) else button
            self.parent_name = parent_name
            self.parent_button = parent_button
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
        self.dbase.message_get_or_create(
            button_id=self.button_id,
            message_data={'state_or_key': self.state_or_key,
                          'reply_text': self.reply_text,
                          'children_buttons': [child.button_id for child in self.children_buttons]}
        )

        # with self.dbase:
        #     message, fact_create = self.tables.messages.get_or_create(button_id=self.button_id)
        #     if message:
        #         message.state_or_key = self.state_or_key
        #         message.reply_text = self.reply_text
        #         message.children_buttons = [child.button_id for child in self.children_buttons]
        #         if fact_create:
        #             self.logger.debug(self.base_sign + f'create new object message: {self.class_name} in DB')
        #         else:
        #             self.logger.debug(self.base_sign + f'update object message: {self.class_name} in DB')


class BaseButton(Base):
    """ Логика - которая будет прописана в дочерних классах выполниться только один раз при старте программы
    динамическая логика должна быть прописана в методе _set_answer_logic. Каждая кнопка при создании автоматически
    добавляется в коллекцию на основе префикса"""

    __instance = None
    __buttons_id = [0, ]
    base_sign = 'BaseButton: '

    __slots__ = ('button_id', 'name', 'url', 'callback', 'parent_id', 'reply_text', 'next_state',
                 'children_buttons', 'children_messages', 'any_data', 'parent_name', 'parent_button', 'class_name')

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, name: str | None = None, callback: str | None = None, new=True,
                 parent_id: int | None = None, parent_name: str | None = None, parent_callback: str | None = None,
                 reply_text: str | None = None, children: list | None = None, messages: dict | None = None,
                 any_data: dict | None = None, next_state: str | None = None, parent_button: Any | None = None):

        if new and self.__class__.__name__ != BaseButton.__name__:
            self.class_name = self.__class__.__name__
            self.button_id = self.__set_button_id()
            self.name = self._set_name() if not name else name
            self.url = self._set_url()
            self.callback = self._set_callback() if not callback else callback
            self.parent_name = parent_name
            self.parent_button = parent_button

            self.parent_id = self._get_button_id(button_id=parent_id, name=parent_name, callback=parent_callback)
            self.reply_text = self._set_reply_text() if not reply_text else reply_text
            self.next_state = self._set_next_state() if not next_state else next_state
            self.any_data = any_data

            self.__save_button()
            self.children_buttons = self._set_children() if not children else children
            self.children_messages = self._set_messages() if not messages else messages
            self._update_children_and_messages()

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
        self.dbase.button_get_or_create(button_id=self.button_id,
                                        button_data={'parent_id': self.parent_id,
                                                     'name': self.name,
                                                     'callback': self.callback,
                                                     'reply_text': self.reply_text
                                                     }
                                        )
        # with self.dbase:
        #     button, fact_create = self.tables.buttons.get_or_create(button_id=self.button_id)
        #     if button:
        #         button.parent_id = self.parent_id
        #         button.name = self.name
        #         button.callback = self.callback
        #         button.reply_text = self.reply_text
        #         button.save()
        #         if fact_create:
        #             self.logger.debug(self.base_sign + f'create new object button: {self.class_name} in DB')
        #         else:
        #             self.logger.debug(self.base_sign + f'update object button: {self.class_name} in DB')

    def _update_children_and_messages(self) -> None:
        """Вызывается один раз при создании singleton экземпляра класса"""
        self.dbase.update_button(
            button_id=self.button_id,
            update_data={'children': [child.button_id for child in self.children_buttons],
                         'messages': [child.state_or_key for child in self.children_messages.values()],
                         }
        )

        # with self.dbase:
        #     if button := self.tables.buttons.get_or_none(button_id=self.button_id):
        #         button.children = [child.button_id for child in self.children_buttons]
        #         button.messages = [child.state_or_key for child in self.children_messages.values()]
        #         button.save()
        #         self.logger.debug(self.base_sign + f'update lists children objects in object button: {self.class_name} in DB')

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


class GoToBack(BaseButton):
    def _set_name(self) -> str:
        return '◀ Назад'

    async def _set_answer_logic(self, update, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        previous_button = await self.button_search_and_action_any_collections(action='get',
                                                                              button_name=data.get('previous_button'))

        result_button = await self.button_search_and_action_any_collections(action='get', button_name='PersonalCabinet')

        if previous_button:
            if parent_prev_button := await self.button_search_and_action_any_collections(
                    action='get', button_name=previous_button.parent_name):
                result_button = parent_prev_button

        if hasattr(result_button.__class__, '_set_answer_logic'):
            reply_text, next_state = await result_button._set_answer_logic(update, state)
        else:
            reply_text, next_state = result_button.reply_text, result_button.next_state

        self.children_buttons = result_button.children_buttons
        return reply_text, next_state


class PostFeedback(BaseButton):
    def _set_name(self) -> str:
        return '📩 Опубликовать'

    async def _set_answer_logic(self, update, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        feed_button = await self.button_search_and_action_any_collections(action='get',
                                                                          button_name=data.get('previous_button'))

        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        seller_token = wb_user.sellerToken
        signature = wb_user.signature_to_answer
        wb_user.unanswered_feedbacks.pop(feed_button.__class__.__name__)

        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )

        feedback_answer_text = feed_button.any_data.get('answer')
        if signature:
            feedback_answer_text += f"\n\n{signature}"

        result, error_text = await self.wb_api.send_feedback(
            seller_token=seller_token,
            x_supplier_id=feed_button.parent_name.lstrip('Supplier'),
            feedback_id=feed_button.__class__.__name__.lstrip('Feedback'),
            feedback_answer__text=feedback_answer_text,
            update=update
        )

        ok_result = "🆗 Ответ на отзыв отправлен успешно"
        bad_result = "⚠ Ошибка ответа на отзыв, попробуйте ещё раз"
        msg = await self.bot.send_message(chat_id=update.from_user.id, text=ok_result if result else bad_result)
        await asyncio.sleep(3)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=msg.message_id)

        supplier_button = await self.button_search_and_action_any_collections(action='get',
                                                                              button_name=feed_button.parent_name)
        self.log(f'result: {result} | error_text: {error_text}', level='warning')
        self.log(f'supplier_button start len children_buttons: '
                 f'{len(supplier_button.children_buttons)}', level='warning')

        if result:
            await self.button_search_and_action_any_collections(action='pop', instance_button=feed_button)
            supplier_button.children_buttons.remove(feed_button)
            self.log(f'supplier_button after remove len children_buttons: {len(supplier_button.children_buttons)}',
                     level='warning')

            was = re.search(r'< \d+ >', supplier_button.name).group(0)
            will_be = f"< {int(was.strip('<> ')) - 1} >"
            supplier_button.name = supplier_button.name.replace(was, will_be)

        self.log(f'supplier_button: {supplier_button}', level='warning')
        self.children_buttons = supplier_button.children_buttons
        return supplier_button.reply_text, supplier_button.next_state


class EditFeedback(BaseButton):
    def _set_name(self) -> str:
        return '✏ Редактировать'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext | None = None):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)

        data = dict()
        if state:
            data = await state.get_data()

        previous_button = await self.button_search_and_action_any_collections(action='get',
                                                                              button_name=data.get('previous_button'))

        reply_text = previous_button.any_data.get('answer')
        self.reply_text = reply_text

        return self.reply_text, self.next_state


class GenerateNewResponseToFeedback(BaseButton):
    def _set_name(self) -> str:
        return '✍ Сгенерировать новый ответ'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext | None = None):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)
        message_waiting = await self.bot.send_message(chat_id=update.from_user.id, text=self.default_generate_answer)

        data = dict()
        if state:
            data = await state.get_data()

        previous_button = await self.button_search_and_action_any_collections(action='get',
                                                                              button_name=data.get('previous_button'))

        reply_feedback = await self.ai.reply_feedback(previous_button.any_data.get('text'))
        previous_button.any_data['answer'] = reply_feedback

        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        if wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__):
            wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__).update({'answer': reply_feedback})

        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )

        self.children_buttons = previous_button.children_buttons
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=message_waiting.message_id)

        new_reply_text = previous_button.reply_text.split('<b>Ответ:</b>\n\n')[0] + \
            '<b>Ответ:</b>\n\n'+f"<code>{previous_button.any_data.get('answer')}</code>"

        previous_button.reply_text = new_reply_text

        return new_reply_text, self.next_state


class DontReplyFeedback(BaseButton):
    def _set_name(self) -> str:
        return '⛔ Не отвечать на отзыв'

    async def _set_answer_logic(self, update: Message, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        removed_button = await self.button_search_and_action_any_collections(action='pop',
                                                                             button_name=data.get('previous_button'))

        supplier_button = await self.button_search_and_action_any_collections(action='get',
                                                                              button_name=removed_button.parent_name)
        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        if rm_feed := wb_user.unanswered_feedbacks.pop(removed_button.__class__.__name__, None):
            wb_user.ignored_feedbacks[removed_button.__class__.__name__] = rm_feed

        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'ignored_feedbacks': wb_user.ignored_feedbacks,
                         'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )

        supplier_button.children_buttons.remove(removed_button)
        self.children_buttons = supplier_button.children_buttons

        # await self.change_name_button(supplier_button, len(self.children_buttons) - 1)
        unfeeds_supplier = [feed for feed in wb_user.unanswered_feedbacks.values()
                            if feed.get('supplier') == supplier_button.__class__.__name__]
        await self.change_name_button(supplier_button, len(unfeeds_supplier))

        return supplier_button.reply_text, supplier_button.next_state


class MessageEditFeedbackAnswer(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:edit_feedback_answer'

    async def _set_answer_logic(self, update: Message, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        previous_button = await self.button_search_and_action_any_collections(action='get',
                                                                              button_name=data.get('previous_button'))
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message_id)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=data.get('last_handler_sent_message_id'))

        new_reply_text = update.text.replace(f'@{BOT_NIKNAME}', '').strip().strip('\n').strip()
        previous_button.any_data['answer'] = new_reply_text

        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        if wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__):
            wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__).update({'answer': new_reply_text})

        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )

        self.children_buttons = previous_button.children_buttons

        new_reply_text = previous_button.reply_text.split('<b>Ответ:</b>\n\n')[0] + \
            '<b>Ответ:</b>\n\n'+f"<code>{previous_button.any_data.get('answer')}</code>"
        previous_button.reply_text = new_reply_text

        return new_reply_text, self.next_state


class DefaultButtonForAUFM(BaseButton):
    # feeds = dict()

    def __call__(self, feed_id, feed_key_name):
        # feed_id = kwargs.get('feed_id')
        # feed_key_name = kwargs.get('feed_key_name')

        self.name, long_feed_id = self.set_button_name(self.name, feed_id)
        self.aufm_feeds_collection[long_feed_id] = feed_key_name

        # print(self.aufm_feeds_collection)

        return self

    @staticmethod
    def set_button_name(start_name: str, button_id: str | int) -> tuple[str, str]:
        if isinstance(button_id, int):
            button_id = str(button_id)
        long_btn_id = button_id.zfill(7)
        return start_name[:-7] + long_btn_id, long_btn_id

    def _set_name(self) -> str:
        return '↘ Перейти к отзыву #0000000'

    def _set_next_state(self) -> str | None:
        return FSMPersonalCabinetStates.edit_feedback_answer

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext | None = None) -> tuple[str | None, str | None]:
        data = dict()
        if state:
            data = await state.get_data()

        # long_feed_id = self.name[-7:]
        long_feed_id = update.message.reply_markup.values.get('inline_keyboard')[0][0].text[-7:]
        feed_key_name = self.aufm_feeds_collection.pop(long_feed_id)
        # print('feed_key_name:', feed_key_name)

        last_call_message_id = data.get('last_call_message_id')
        # print(last_call_message_id)

        feed_btn = await self.button_search_and_action_any_collections(action='pop', button_name=feed_key_name)
        # print('feed_btn:', feed_btn)

        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=last_call_message_id)

        reply_text = feed_btn.reply_text if feed_btn.reply_text else self.default_bad_text

        self.children_buttons = feed_btn.children_buttons

        return reply_text, self.next_state


class Utils(Base):

    list_children_buttons = [PostFeedback(), EditFeedback(),
                             GenerateNewResponseToFeedback(), DontReplyFeedback(), GoToBack(new=False)]
    message_to_edit_feedback = {FSMPersonalCabinetStates.edit_feedback_answer: MessageEditFeedbackAnswer()}

    @classmethod
    async def send_request_for_phone_number(cls, update, state):
        reply_text = 'Пожалуйста, введите номер телефона, указанный при регистрации в кабинете Wildberries. ' \
                     'Формат +7**********'
        next_state = FSMUtilsStates.message_after_user_enters_phone
        return reply_text, next_state

    @classmethod
    async def send_request_for_sms_code(cls, update, state, phone):

        input_string = update.text.strip() if not phone else phone
        phone = await cls.m_utils.check_data(input_string)
        if phone and phone.isdigit() and len(phone) == 11:
            sms_token = await cls.wb_api.send_phone_number(phone, update)

            cls.dbase.update_wb_user(user_id=update.from_user.id,
                                     update_data={'phone': phone, 'sms_token': sms_token})

            reply_text = 'Пожалуйста, введите код который пришёл в кабинет покупателя ' \
                         'Wildberries либо по смс на указанный номер телефона:'
            next_state = FSMUtilsStates.message_after_user_enters_sms_code
        else:
            reply_text = "Ошибка введите номер телефона"
            next_state = None
        return reply_text, next_state

    @classmethod
    async def get_access_to_wb_api(cls, update, state, phone:  str | int | None = None,
                                   sms_code: str | int | None = None) -> tuple | str:

        wb_user = cls.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        seller_token = wb_user.sellerToken
        passport_token = wb_user.passportToken
        sms_token = wb_user.sms_token

        if not seller_token and not passport_token and not phone and not sms_code:
            reply_text, next_state = await cls.send_request_for_phone_number(update=update, state=state)
            return reply_text, next_state

        if phone:
            reply_text, next_state = await cls.send_request_for_sms_code(update=update, state=state, phone=phone)
            return reply_text, next_state

        elif sms_code and sms_token:
            seller_token = await cls.wb_api.send_sms_code(sms_code=sms_code, sms_token=sms_token, update=update)
            if seller_token:
                wb_user_id = await cls.wb_api.introspect_seller_token(seller_token=seller_token, update=update)
                if wb_user_id:
                    passport_token = await cls.wb_api.get_passport_token(seller_token=seller_token, update=update)

                    cls.dbase.update_wb_user(
                        user_id=update.from_user.id,
                        update_data={'WB_user_id': wb_user_id, 'passportToken': passport_token}
                    )

        return seller_token

    @classmethod
    async def suppliers_buttons_logic(cls, update: Message | CallbackQuery | None = None,
                                      state: FSMContext | None = None, user_id: int | None = None):
        suppliers = []
        user_id = user_id if user_id else update.from_user.id
        wb_user = cls.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        wb_user_suppliers = wb_user.suppliers
        seller_token = wb_user.sellerToken

        cls.logger.debug(f'Utils: get suppliers buttons names from DB {wb_user_suppliers=}')

        if wb_user_suppliers:
            suppliers = await cls.get_many_buttons_from_any_collections(get_buttons_list=wb_user_suppliers.keys())
            cls.logger.debug(f'Utils: get from collections buttons {suppliers=}')

            if wb_user_suppliers and not suppliers:
                suppliers = await cls.utils_get_or_create_buttons(collection=wb_user_suppliers, class_type='supplier',
                                                                  update=update, user_id=user_id)
                cls.logger.debug(f'Utils: create buttons {suppliers=}')

        else:
            if seller_token:
                if suppliers := await cls.wb_api.get_suppliers(seller_token=seller_token, update=update,
                                                               user_id=user_id):
                    suppliers = await cls.utils_get_or_create_buttons(suppliers, class_type='supplier', update=update,
                                                                      user_id=user_id)

            else:
                seller_token = await cls.get_access_to_wb_api(update=update, state=state)
                if not isinstance(seller_token, tuple):
                    cls.logger.debug(f'Utils: not suppliers recursive call suppliers_buttons_logic {suppliers=}')
                    suppliers = await cls.suppliers_buttons_logic(update=update, state=state, user_id=user_id)

        return suppliers

    @classmethod
    async def feedback_buttons_logic(cls, supplier: dict | str, update: Message | CallbackQuery | None = None,
                                     user_id: int | None = None) -> list:
        supplier_name_key = list(supplier.keys())[0] if isinstance(supplier, dict) else supplier
        user_id = user_id if user_id else update.from_user.id
        feedbacks = None

        if wb_user := cls.dbase.wb_user_get_or_none(user_id=user_id):
            feedbacks = wb_user.unanswered_feedbacks

        if feedbacks:
            """Выбираем неотвеченные отзывы конкретного supplier из БД"""
            feedbacks = {feedback_id: feedback_data for feedback_id, feedback_data
                         in dict(itertools.islice(feedbacks.items(), NUM_FEED_BUTTONS)).items()
                         if feedback_data.get('supplier') == supplier_name_key}
        else:
            """Если в БД нет отзывов делаем запрос к WB API"""
            msg = await cls.bot.send_message(chat_id=user_id, text=cls.default_download_information)
            feedbacks, supplier_total_feeds = await cls.wb_api.get_feedback_list(seller_token=wb_user.sellerToken,
                                                                                 supplier=supplier, user_id=user_id)
            await cls.bot.delete_message(chat_id=user_id, message_id=msg.message_id)

        """Возвращаем список объектов BaseButton кнопок-отзывов"""
        return await cls.utils_get_or_create_buttons(collection=feedbacks, class_type='feedback',
                                                     update=update, supplier_name_key=supplier_name_key)

    @classmethod
    async def create_button_dynamically(cls, data: dict, class_type: str, update: Message | CallbackQuery | None = None,
                                        supplier_name_key: str | None = None, user_id: int | None = None):
        """Рекурсивное создание кнопок кабинетов(supplier) и отзывов"""
        button = None
        reply_text = '<b>Выберите отзыв:</b>'
        user_id = user_id if user_id else update.from_user.id

        for object_id, object_data in data.items():
            cls.logger.debug(f'Utils: create_button: {object_id}, supplier: {supplier_name_key}')
            if object_id.startswith('Feedback'):
                dt, tm = object_data.get("createdDate")[:16].split("T")
                dt_tm = ' '.join(('-'.join(dt.split('-')[::-1]), tm))

                reply_text = '<b>Выберите отзыв:</b>' if class_type == 'Supplier' else \
                             f'<b>Товар:</b> {object_data.get("productName")}\n' \
                             f'<b>Дата:</b> {dt_tm}\n' \
                             f'<b>Оценка:</b> {object_data.get("productValuation")}\n' \
                             f'<b>Текст отзыва:</b> {object_data.get("text")}\n\n' \
                             f'<b>Ответ:</b>\n\n<code>{object_data.get("answer")}</code>'

            parent_button = cls.button_search_and_action_any_collections(
                'get', button_name='WildberriesCabinet' if class_type == 'Supplier' else supplier_name_key)

            button = type(object_id, (BaseButton, ), {})(
                name=object_data.get('button_name'),
                parent_name='WildberriesCabinet' if class_type == 'Supplier' else supplier_name_key,
                parent_button=parent_button,
                reply_text=reply_text,
                any_data=object_data,
                messages=cls.message_to_edit_feedback if class_type == 'Feedback' else None,
                next_state=FSMPersonalCabinetStates.edit_feedback_answer if class_type == 'Feedback' else None
            )

            # тут создаются новые кнопки отзывов
            children = cls.list_children_buttons if class_type == 'Feedback' else \
                await cls.feedback_buttons_logic(supplier=data, update=update, user_id=user_id)

            button.children_buttons = children

            # TODO подумать нужно ли это поидее если коллекцию хранить в БД то нужно
            button._update_children_and_messages()

            # TODO если коллекцию хранить в БД то имя тоже нужно записывать
            if isinstance(button.name, str) and class_type == 'Supplier':
                wb_user = cls.dbase.wb_user_get_or_none(user_id=user_id)
                unfeeds_supplier = [feed for feed in wb_user.unanswered_feedbacks.values()
                                    if feed.get('supplier') == button.__class__.__name__]
                # button.name += f' < {len(children)-1 if children else 0} >'
                button.name += f' < {len(unfeeds_supplier)} >'

            button.reply_text = '📭 <b>Отзывов пока нет</b>' if len(children)-1 <= 0 else reply_text

        return button

    @classmethod
    async def utils_get_or_create_buttons(cls, collection: dict, class_type: str,
                                          update: Message | CallbackQuery | None = None,
                                          supplier_name_key: str | None = None,
                                          user_id: int | None = None) -> list:
        class_type = class_type.title()
        user_id = user_id if user_id else update.from_user.id

        if class_type not in ['Supplier', 'Feedback']:
            raise ValueError('class_type должен быть Supplier или Feedback')

        __buttons = list()

        for object_id, object_data in collection.items():
            """Проверяем существует ли объект-кнопка BaseButton В какой-либо коллекции"""
            button = await cls.button_search_and_action_any_collections(action='get', button_name=object_id)

            if not button:
                """Если нет создаем новый объект"""
                button = await cls.create_button_dynamically(
                    data={object_id: object_data}, class_type=class_type, update=update, user_id=user_id,
                    supplier_name_key=supplier_name_key
                )

            __buttons.append(button)

        __buttons.append(GoToBack(new=False))

        return __buttons
