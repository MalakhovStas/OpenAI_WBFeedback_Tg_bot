import asyncio
from abc import ABC
from typing import Any

from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery
from loguru import logger

from config import BOT_NIKNAME, NUM_FEED_BUTTONS, FACE_BOT
from database.db_utils import Tables
from managers.db_manager import DBManager
from utils import misc_utils
from utils.states import FSMPersonalCabinetStates, FSMUtilsStates


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

    default_bad_text = 'Нет данных'
    default_service_in_dev = '🛠 Сервис в разработке, в ближайшее время функционал будет доступен'
    default_incorrect_data_input_text = FACE_BOT + 'Введены некорректные данные - {text}'
    default_generate_answer = FACE_BOT + '✍ Генерирую ответ, немного подождите пожалуйста ...'
    default_download_information = FACE_BOT + '🌐 {about}\nнемного подождите пожалуйста ...'

    # general_collection = {'general_messages': {},
    #                       'general_buttons': {},
    #                       'user_id': {'updates_data': {}, 'suppliers': {}, 'feedbacks': {}, 'aufm_catalog': {}}}

    general_collection = dict()
    general_collection_dump = dict()
    # message_store = dict()
    # button_store = dict()
    # supplier_collection = dict()
    # feedback_collection = dict()
    # aufm_catalog = dict()
    #
    # updates_data = dict()

    def log(self, message, level: str | None = None):
        text = f'class: {self.__class__.__name__}: ' + message

        level = 'debug' if not level else level

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
        """Установка следующего состояния по умолчанию None"""
        return None

    def _set_children(self) -> list:
        """ Установка дочерних кнопок по умолчанию list()"""
        return list()

    @classmethod
    async def get_many_buttons_from_any_collections(cls, get_buttons_list: list | tuple,
                                                    user_id: int | None = None) -> Any | None:
        cls.logger.debug(f'Base: get_many_buttons_from_any_collections -> get_buttons_list: {get_buttons_list}')
        result_buttons_list = list()

        if get_buttons_list:
            for button_name in get_buttons_list:
                if result_button := await cls.button_search_and_action_any_collections(user_id=user_id, action='get',
                                                                                       button_name=button_name):
                    result_buttons_list.append(result_button)

        cls.logger.debug(f'Base: get_many_buttons_from_any_collections -> {"OK" if result_buttons_list else "BAD"} '
                         f'get_buttons_list: {get_buttons_list}, return result: {result_buttons_list}')
        # result_buttons_list.append(GoToBack(new=False))
        return result_buttons_list

    @classmethod
    async def button_search_and_action_any_collections(cls, action: str, button_name: str | None = None,
                                                       instance_button: Any | str | None = None,
                                                       user_id: str | int | None = None,
                                                       update: Message | CallbackQuery | None = None,
                                                       message: bool = False,
                                                       updates_data: bool = False,
                                                       aufm_catalog_key: str | None = None
                                                       ) -> Any | None:

        if update and not user_id:
            user_id = update.from_user.id

        if user_id:
            cls.general_collection.setdefault(user_id, {'updates_data': {},
                                                        'suppliers': {},
                                                        'feedbacks': {},
                                                        'aufm_catalog': {}})

            # cls.general_collection_dump.setdefault(user_id, {'updates_data': {},
            #                                             'suppliers': {},
            #                                             'feedbacks': {},
            #                                             'aufm_catalog': {}})

        if aufm_catalog_key:
            if action == 'add':
                cls.general_collection.get(user_id).get('aufm_catalog')[aufm_catalog_key] = button_name
                # cls.general_collection_dump.get(user_id).get('aufm_catalog')[aufm_catalog_key] = button_name
                return True
            elif action == 'pop':
                button_name = cls.general_collection.get(user_id).get('aufm_catalog').pop(aufm_catalog_key, None)
                # cls.general_collection_dump.get(user_id).get('aufm_catalog').pop(aufm_catalog_key, None)
                action = 'get'
            else:
                raise ValueError(f'aufm_catalog не поддерживает {action=}')

        if not button_name and not instance_button:
            raise ValueError(f'Чтобы выполнить {action=} необходимо передать button_name или instance_button')

        if instance_button and not aufm_catalog_key and not updates_data:
            button_name = instance_button.class_name

        if button_name.startswith('Supplier'):
            collection_name = 'suppliers'

        elif button_name.startswith('Feedback'):
            collection_name = 'feedbacks'

        else:
            if message:
                collection_name = 'general_messages'
            elif updates_data:
                collection_name = 'updates_data'
            else:
                collection_name = 'general_buttons'

        if action == 'add':
            if instance_button or updates_data:
                if collection_name in ['general_buttons', 'general_messages']:
                    cls.general_collection.setdefault(collection_name, dict())[button_name] = instance_button
                    # cls.general_collection_dump.setdefault(collection_name, dict())[button_name] = {attr: getattr(instance_button, attr) for attr in instance_button.__slots__}
                else:
                    cls.general_collection.get(user_id).get(collection_name)[button_name] = instance_button
                    # if updates_data:
                    #     cls.general_collection_dump.get(user_id).get(collection_name)[button_name] = instance_button
                    # else:
                    #     cls.general_collection_dump.get(user_id).get(collection_name)[button_name] = {attr: getattr(instance_button, attr) for attr in instance_button.__slots__}

                button = instance_button
            else:
                raise ValueError(f'Чтобы выполнить {action=} в {collection_name=}, '
                                 f'необходимо передать instance_button -> {button_name=}')
        elif action == 'get':
            if collection_name in ['general_buttons', 'general_messages']:
                button = cls.general_collection.setdefault(collection_name, dict()).get(button_name)
            else:
                button = cls.general_collection.get(user_id).get(collection_name).get(button_name)

        elif action == 'pop':
            if collection_name in ['general_buttons', 'general_messages']:
                button = cls.general_collection.setdefault(collection_name, dict()).pop(button_name, None)
                # cls.general_collection_dump.setdefault(collection_name, dict()).pop(button_name, None)
            else:
                button = cls.general_collection.get(user_id).get(collection_name).pop(button_name, None)
                # cls.general_collection_dump.get(user_id).get(collection_name).pop(button_name, None)

        else:
            button = None
        # if not isinstance(button, (int, str)):
            # cls.general_collection_dump[button.class_name] = {attr: getattr(button, attr) for attr in button.__slots__}
        cls.logger.debug(f'Base: {"OK" if button else "BAD"} -> {action=} | {collection_name=} | return {button=}')
        return button

    @classmethod
    async def pop_feed_and_change_supplier_name_button(cls, user_id, feed_button, supplier_button):
        """ Удаляет отзыв из коллекции и из children_buttons кнопки supplier,
            а также в её имени меняет количество отзывов на -1 """

        # cls.logger.debug(f'start {len(supplier_button.children_buttons)=}')
        await cls.button_search_and_action_any_collections(user_id=user_id, action='pop', instance_button=feed_button)
        supplier_button.children_buttons.remove(feed_button)
        # cls.logger.debug(f'after remove {len(supplier_button.children_buttons)=}')
        await cls.m_utils.change_name_button(button=supplier_button, minus_one=True)

    @classmethod
    async def update_feed_answer(cls, user_id, button, new_answer):
        button.any_data['answer'] = new_answer

        wb_user = cls.dbase.wb_user_get_or_none(user_id=user_id)
        if wb_user.unanswered_feedbacks.get(button.class_name):
            wb_user.unanswered_feedbacks.get(button.class_name).update({'answer': new_answer})

        cls.dbase.update_wb_user(
            user_id=user_id,
            update_data={'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )


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
                 children_buttons: list | None = None, parent_name: str | None = None,
                 parent_button: Any | None = None):

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

            # self.message_store.setdefault(self.state_or_key, self)
            self.general_collection.setdefault('general_messages', dict())[self.state_or_key] = self
            # await self.button_search_and_action_any_collections(
            #     action='add', button_name=self.state_or_key, instance_button=self, message=True)

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
                 any_data: dict | None = None, next_state: str | None = None, parent_button: Any | None = None,
                 user_id: str | None = None):

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

            # self.message_store.update(self.children_messages)

            # if self.__class__.__name__.startswith('Supplier'):
            # await self.button_search_and_action_any_collections(
            #     user_id=user_id, action='add', button_name=self.class_name, instance_button=self)

            if self.class_name.startswith('Supplier'):
                self.general_collection.get(user_id).get('suppliers')[self.class_name] = self

                # self.supplier_collection[self.__class__.__name__] = self
                # self.supplier_collection[self.class_name] = self

            elif self.class_name.startswith('Feedback'):
                self.general_collection.get(user_id).get('feedbacks')[self.class_name] = self

                # self.feedback_collection[self.__class__.__name__] = self
                # self.feedback_collection[self.class_name] = self
                # print('создал и добавляю кнопку в коллекцию:', self)
                # print('длина коллекции feedbacks:', len(self.feedback_collection))
            else:
                self.general_collection.setdefault('general_buttons', dict())[self.class_name] = self
                # self.button_store[self.__class__.__name__] = self
                # self.button_store[self.class_name] = self

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

    def _update_children_and_messages(self) -> None:
        """Вызывается один раз при создании singleton экземпляра класса"""
        self.dbase.update_button(
            button_id=self.button_id,
            update_data={'children': [child.button_id for child in self.children_buttons],
                         'messages': [child.state_or_key for child in self.children_messages.values()],
                         }
        )

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

    #TODO нигде не используется возомжно не нужно
    # async def get_parent(self):
    #     return await self.button_search_and_action_any_collections(user_id=user_id, action='get',
    #                                                                button_name=self.parent_name)


class GoToBack(BaseButton):
    def _set_name(self) -> str:
        return '◀ Назад'

    async def _set_answer_logic(self, update, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()
            
        previous_button_name = await self.button_search_and_action_any_collections(
            user_id=update.from_user.id, action='get', button_name='previous_button', updates_data=True)
        # data.get('previous_button')
        previous_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                              button_name=previous_button_name)

        result_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                            button_name='PersonalCabinet')

        if previous_button:
            parent_name = previous_button.parent_name if previous_button.parent_name else 'MainMenu'
            if parent_prev_button := await self.button_search_and_action_any_collections(
                    user_id=update.from_user.id, action='get', button_name=parent_name):
                result_button = parent_prev_button

        if hasattr(result_button.__class__, '_set_answer_logic'):
            reply_text, next_state = await result_button._set_answer_logic(update, state)
        else:
            reply_text, next_state = result_button.reply_text, result_button.next_state

        self.children_buttons = result_button.children_buttons
        return reply_text, next_state


class ParsingFeedbackHasBeenProcessed(BaseButton):
    def _set_name(self) -> str:
        return '🗑 Отзыв опубликован'

    async def _set_answer_logic(self, update, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        feed_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                          button_name=data.get('previous_button'))

        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        wb_user.unanswered_feedbacks.pop(feed_button.class_name)
        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )

        text_result = FACE_BOT + "🆗 Отзыв удален из списка"
        second_msg = await self.bot.send_message(chat_id=update.from_user.id, text=text_result)
        await asyncio.sleep(1)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=second_msg.message_id)

        supplier_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                              button_name=feed_button.parent_name)
        await self.pop_feed_and_change_supplier_name_button(user_id=update.from_user.id, feed_button=feed_button,
                                                            supplier_button=supplier_button)
        self.children_buttons = supplier_button.children_buttons

        return supplier_button.reply_text, supplier_button.next_state


class PostFeedback(BaseButton):
    def _set_name(self) -> str:
        return '📩 Опубликовать'

    async def _set_answer_logic(self, update, state: FSMContext | None = None):
        data = dict()
        first_msg = await self.bot.send_message(chat_id=update.from_user.id,
                                                text=FACE_BOT + '📩 Отправляю ответ на отзыв...')

        if state:
            data = await state.get_data()

        feed_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                          button_name=data.get('previous_button'))

        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        seller_token = wb_user.sellerToken
        signature = wb_user.signature_to_answer

        feedback_answer_text = feed_button.any_data.get('answer')
        if signature:
            feedback_answer_text += f"\n\n{signature}"

        result = await self.wb_api.send_feedback(
            seller_token=seller_token,
            x_supplier_id=feed_button.parent_name.lstrip('Supplier'),
            feedback_id=feed_button.class_name.lstrip('Feedback'),
            feedback_answer__text=feedback_answer_text,
            update=update
        )

        if result:
            wb_user.unanswered_feedbacks.pop(feed_button.class_name)

            self.dbase.update_wb_user(
                user_id=update.from_user.id,
                update_data={'unanswered_feedbacks': wb_user.unanswered_feedbacks}
            )

            text_result = FACE_BOT + "🆗 Ответ на отзыв отправлен успешно"
        else:
            text_result = FACE_BOT + "⚠ Ошибка ответа на отзыв, попробуйте ещё раз"

        await self.bot.delete_message(chat_id=update.from_user.id, message_id=first_msg.message_id)
        second_msg = await self.bot.send_message(chat_id=update.from_user.id, text=text_result)
        await asyncio.sleep(2)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=second_msg.message_id)
        supplier_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                              button_name=feed_button.parent_name)
        if result:
            await self.pop_feed_and_change_supplier_name_button(user_id=update.from_user.id, feed_button=feed_button,
                                                                supplier_button=supplier_button)
        self.children_buttons = supplier_button.children_buttons

        return supplier_button.reply_text, supplier_button.next_state


class EditFeedback(BaseButton):
    def _set_name(self) -> str:
        return '✏ Редактировать'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext | None = None):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)

        data = await state.get_data() if state else dict()

        previous_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
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

        previous_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                              button_name=data.get('previous_button'))

        ai_answer = await self.ai.reply_feedback(previous_button.any_data.get('text'))

        await self.update_feed_answer(user_id=update.from_user.id, button=previous_button, new_answer=ai_answer)

        self.children_buttons = previous_button.children_buttons
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=message_waiting.message_id)

        new_reply_text = previous_button.reply_text.split('<b>Ответ:</b>\n\n')[0] + \
            '<b>Ответ:</b>\n\n' + f"<code>{previous_button.any_data.get('answer')}</code>"

        previous_button.reply_text = new_reply_text

        return new_reply_text, self.next_state


class DontReplyFeedback(BaseButton):
    def _set_name(self) -> str:
        return '⛔ Не отвечать на отзыв'

    async def _set_answer_logic(self, update: Message, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        removed_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='pop',
                                                                             button_name=data.get('previous_button'))

        supplier_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                              button_name=removed_button.parent_name)
        wb_user = self.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        if rm_feed := wb_user.unanswered_feedbacks.pop(removed_button.__class__.__name__, None):
            wb_user.ignored_feedbacks[removed_button.__class__.__name__] = rm_feed

        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'ignored_feedbacks': wb_user.ignored_feedbacks,
                         'unanswered_feedbacks': wb_user.unanswered_feedbacks}
        )

        if removed_button in supplier_button.children_buttons:
            supplier_button.children_buttons.remove(removed_button)

        self.children_buttons = supplier_button.children_buttons

        unfeeds_supplier = [feed for feed in wb_user.unanswered_feedbacks.values()
                            if feed.get('supplier') == supplier_button.class_name]
        await self.m_utils.change_name_button(button=supplier_button, num=len(unfeeds_supplier))

        return supplier_button.reply_text, supplier_button.next_state


class MessageEditFeedbackAnswer(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:edit_feedback_answer'

    async def _set_answer_logic(self, update: Message, state: FSMContext | None = None):
        data = dict()
        if state:
            data = await state.get_data()

        previous_button = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='get',
                                                                              button_name=data.get('previous_button'))
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message_id)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=data.get('last_handler_sent_message_id'))

        new_reply_text = update.text.replace(f'@{BOT_NIKNAME}', '').strip().strip('\n').strip()

        await self.update_feed_answer(user_id=update.from_user.id, button=previous_button, new_answer=new_reply_text)

        self.children_buttons = previous_button.children_buttons

        new_reply_text = previous_button.reply_text.split('<b>Ответ:</b>\n\n')[0] + \
            '<b>Ответ:</b>\n\n' + f"<code>{previous_button.any_data.get('answer')}</code>"
        previous_button.reply_text = new_reply_text

        return new_reply_text, self.next_state


class DefaultButtonForAUFMGoToFeed(BaseButton):

    def __call__(self, user_id, feedback_button):  #feed_id, feed_key_name):
        long_feed_id = self.m_utils.set_button_name(feedback_button.button_id)
        # self.aufm_feeds_collection[long_feed_id] = feed_key_name
        self.button_search_and_action_any_collections(
            user_id=user_id, action='add', button_name=feedback_button.class_name, aufm_catalog_key=long_feed_id)

        return self

    def _set_name(self) -> str:
        return '↘ Перейти к отзыву #0000000'

    def _set_next_state(self) -> str | None:
        return FSMPersonalCabinetStates.edit_feedback_answer

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext | None = None
                                ) -> tuple[str | None, str | None]:
        data = dict()
        if state:
            data = await state.get_data()

        # long_feed_id -> 0000058
        long_feed_id = update.message.reply_markup.values.get('inline_keyboard')[0][0].text[-7:]
        # feed_key_name = self.aufm_feeds_collection.pop(long_feed_id)
        feed_btn = await self.button_search_and_action_any_collections(user_id=update.from_user.id, action='pop',
                                                                       aufm_catalog_key=long_feed_id)
        previous_button = data.get('previous_button')
        # feed_btn = await self.button_search_and_action_any_collections(
        #     user_id=update.from_user.id, action='get', button_name=feed_key_name)

        from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageIdentifierNotSpecified
        # msg_id_to_delete = self.updates_data.get("last_handler_sent_message_id")
        msg_id_to_delete = await self.button_search_and_action_any_collections(
            user_id=update.from_user.id, action='get', button_name='last_handler_sent_message_id', updates_data=True)
        try:
            await self.bot.delete_message(chat_id=update.from_user.id, message_id=msg_id_to_delete)

        except (MessageToDeleteNotFound, MessageIdentifierNotSpecified) as exc:
            self.logger.warning(self.base_sign + f'{msg_id_to_delete=} NOT found in chat_id: '
                                                 f'{update.from_user.id} | {exc=} | {previous_button=}')

        update.data = feed_btn.class_name

        reply_text = feed_btn.reply_text if feed_btn.reply_text else self.default_bad_text

        self.children_buttons = feed_btn.children_buttons

        return reply_text, self.next_state


class Utils(Base):
    list_children_buttons = [PostFeedback(), EditFeedback(),
                             GenerateNewResponseToFeedback(), DontReplyFeedback(), GoToBack()]
    message_to_edit_feedback = {FSMPersonalCabinetStates.edit_feedback_answer: MessageEditFeedbackAnswer()}

    @classmethod
    async def send_request_for_phone_number(cls, update, state):
        reply_text = FACE_BOT + 'Пожалуйста, введите номер телефона, указанный при регистрации в ' \
                                'кабинете Wildberries. Формат +7**********'
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

            reply_text = FACE_BOT + 'Пожалуйста, введите код который пришёл в кабинет покупателя ' \
                                    'Wildberries либо по смс на указанный номер телефона:'
            next_state = FSMUtilsStates.message_after_user_enters_sms_code
        else:
            reply_text = FACE_BOT + "Ошибка ввода данных, пожалуйста введите номер телефона"
            next_state = None
        return reply_text, next_state

    @classmethod
    async def get_access_to_wb_api(cls, update, state, phone: str | int | None = None,
                                   sms_code: str | int | None = None) -> tuple | str:
        """ Для проверки или регистрации доступа к личному кабинету wildberries """
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
    async def api_suppliers_buttons_logic(cls, update: Message | CallbackQuery | None = None,
                                          state: FSMContext | None = None, user_id: int | None = None) -> list:
        suppliers = []
        user_id = user_id if user_id else update.from_user.id
        wb_user = cls.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        seller_token = wb_user.sellerToken
        wb_user_suppliers = {supplier_name: supplier_data for supplier_name, supplier_data in wb_user.suppliers.items()
                             if supplier_data.get('mode') == 'API'}

        cls.logger.debug(f'Utils: get suppliers buttons names from DB {wb_user_suppliers=}')

        if wb_user_suppliers:
            suppliers = await cls.get_many_buttons_from_any_collections(get_buttons_list=list(wb_user_suppliers.keys()),
                                                                        user_id=user_id)
            cls.logger.debug(f'Utils: get from collections buttons {suppliers=}')

            if not suppliers:
                suppliers = await cls.utils_get_or_create_buttons(collection=wb_user_suppliers, class_type='supplier',
                                                                  update=update, user_id=user_id)
                cls.logger.debug(f'Utils: create buttons {suppliers=}')

        else:
        #todo &&&&&&&&&&&?????????????
        # if not wb_user_suppliers or all([len(suppl.children_buttons) < 2 for suppl in suppliers if suppl.class_name != 'GoToBack']):
            if seller_token:
                if suppliers := await cls.wb_api.get_suppliers(seller_token=seller_token, update=update,
                                                               user_id=user_id):
                    suppliers = await cls.utils_get_or_create_buttons(suppliers, class_type='supplier', update=update,
                                                                      user_id=user_id)

            else:
                seller_token = await cls.get_access_to_wb_api(update=update, state=state)
                if not isinstance(seller_token, tuple):
                    cls.logger.debug(f'Utils: not suppliers recursive call suppliers_buttons_logic {suppliers=}')
                    suppliers = await cls.api_suppliers_buttons_logic(update=update, state=state, user_id=user_id)

        # print([len(suppl.children_buttons) < 2 for suppl in suppliers if suppl.class_name != 'GoToBack'])
        return suppliers

    @classmethod
    async def parsing_suppliers_buttons_logic(cls, update: Message | CallbackQuery | None = None,
                                              state: FSMContext | None = None, user_id: int | None = None) -> list:
        suppliers = []
        user_id = user_id if user_id else update.from_user.id
        wb_user = cls.dbase.wb_user_get_or_none(user_id=update.from_user.id)
        wb_user_suppliers = {supplier_name: supplier_data for supplier_name, supplier_data in wb_user.suppliers.items()
                             if supplier_data.get('mode') == 'PARSING'}
        # print(f'parsing_suppliers_buttons_logic: {wb_user_suppliers=}')

        cls.logger.debug(f'Utils: get suppliers buttons names from DB {wb_user_suppliers=}')

        if wb_user_suppliers:
            suppliers = await cls.get_many_buttons_from_any_collections(get_buttons_list=list(wb_user_suppliers.keys()),
                                                                        user_id=user_id)
            # print('suppliers:', suppliers)
            cls.logger.debug(f'Utils: get from collections buttons {suppliers=}')

            # print(f'{len(wb_user_suppliers)=} | {len(suppliers)=}')
            if not suppliers or len(wb_user_suppliers) > len(suppliers):
                suppliers = await cls.utils_get_or_create_buttons(collection=wb_user_suppliers, class_type='supplier',
                                                                  update=update, user_id=user_id)
                cls.logger.debug(f'Utils: create buttons {suppliers=}')
        # print(f'parsing_suppliers_buttons_logic: {suppliers=}')
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
            # feedbacks = {feedback_id: feedback_data for feedback_id, feedback_data
            #              in dict(itertools.islice(feedbacks.items(), NUM_FEED_BUTTONS)).items()
            #              if feedback_data.get('supplier') == supplier_name_key}

            feedbacks = {feedback_id: feedback_data for feedback_id, feedback_data in feedbacks.items()
                         if feedback_data.get('supplier') == supplier_name_key}
            feedbacks = dict(list(feedbacks.items())[0:NUM_FEED_BUTTONS])
            # print('!!!!!!!!!!!!!!!!!!!!!', supplier_name_key == 'SupplierParsing252218', feedbacks)

        # else:
        if not feedbacks:
            supplier_btn_name = list(supplier.values())[0].get('button_name')
            """Если в БД нет отзывов конкретного supplier делаем запрос к WB API или WB PARSING"""
            msg = await cls.bot.send_message(chat_id=user_id, text=cls.default_download_information.format(
                about=f'Загружаю информацию о отзывах магазина: \n<b>{supplier_btn_name}</b>'))

            if supplier_name_key.startswith('SupplierParsing'):
                feedbacks, supplier_total_feeds = await cls.wb_parsing(supplier_id=supplier_name_key, update=update)
            else:
                feedbacks, supplier_total_feeds = await cls.wb_api.get_feedback_list(seller_token=wb_user.sellerToken,
                                                                                     supplier=supplier, user_id=user_id)
            await cls.bot.delete_message(chat_id=user_id, message_id=msg.message_id)

        """Возвращаем список объектов BaseButton кнопок-отзывов"""
        return await cls.utils_get_or_create_buttons(collection=feedbacks, class_type='feedback', user_id=user_id,
                                                     update=update, supplier_name_key=supplier_name_key)

    @classmethod
    async def create_button_dynamically(cls, data: dict, class_type: str, update: Message | CallbackQuery | None = None,
                                        supplier_name_key: str | None = None, user_id: int | None = None):
        """Рекурсивное создание кнопок кабинетов(supplier) и отзывов"""
        button = None
        reply_text = FACE_BOT + '<b>Выберите отзыв:</b>'
        user_id = user_id if user_id else update.from_user.id

        for object_id, object_data in data.items():
            cls.logger.debug(f'Utils: create_button: {object_id}, supplier: {supplier_name_key}')

            if object_id.startswith('Feedback'):
                dt_tm = await cls.m_utils.reversed_date_time_feedback(object_data)

                reply_text = '<b>Выберите отзыв:</b>' if class_type == 'Supplier' else \
                    f'<b>Товар:</b> {object_data.get("productName")}\n' \
                    f'<b>Дата:</b> {dt_tm}\n' \
                    f'<b>Оценка:</b> {object_data.get("productValuation")}\n' \
                    f'<b>Текст отзыва:</b> {object_data.get("text")}\n\n' \
                    f'<b>Ответ:</b>\n\n<code>{object_data.get("answer")}</code>'

            parent_button = await cls.button_search_and_action_any_collections(
                user_id=user_id, action='get',
                button_name='WildberriesCabinet' if class_type == 'Supplier' else supplier_name_key
            )

            button = type(object_id, (BaseButton,), {})(
                name=object_data.get('button_name'),
                parent_name='WildberriesCabinet' if class_type == 'Supplier' else supplier_name_key,
                parent_button=parent_button,
                reply_text=reply_text,
                any_data=object_data,
                messages=cls.message_to_edit_feedback if class_type == 'Feedback' else None,
                next_state=FSMPersonalCabinetStates.edit_feedback_answer if class_type == 'Feedback' else None,
                user_id=user_id
            )

            # тут создаются новые кнопки отзывов
            if class_type == 'Feedback':
                if supplier_name_key.startswith('SupplierParsing'):
                    children = [ParsingFeedbackHasBeenProcessed(), *cls.list_children_buttons[1:]]
                else:
                    children = cls.list_children_buttons

            elif object_id.startswith('SupplierParsing'):
                children = await cls.feedback_buttons_logic(supplier=data, update=update, user_id=user_id)
                # todo ллогика создания отзывов
            else:
                children = await cls.feedback_buttons_logic(supplier=data, update=update, user_id=user_id)
            button.children_buttons = children

            # TODO подумать нужно ли это поидее если коллекцию хранить в БД то нужно
            button._update_children_and_messages()

            # TODO если коллекцию хранить в БД то имя тоже нужно записывать
            if isinstance(button.name, str) and class_type == 'Supplier':
                wb_user = cls.dbase.wb_user_get_or_none(user_id=user_id)
                unfeeds_supplier = [feed for feed in wb_user.unanswered_feedbacks.values()
                                    if feed.get('supplier') == button.class_name]
                # button.name += f' < {len(children)-1 if children else 0} >'
                button.name += f' < {len(unfeeds_supplier)} >'

            button.reply_text = FACE_BOT + '<b>В этом магазине отзывов пока нет</b>' \
                if len(children) - 1 <= 0 else reply_text
        # print('len feedback_collection:', len(cls.feedback_collection))
        # print('len supplier_collection:', len(cls.supplier_collection))
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
            button = await cls.button_search_and_action_any_collections(user_id=user_id, action='get',
                                                                        button_name=object_id)
            if not button:
                """Если нет создаем новый объект"""
                button = await cls.create_button_dynamically(
                    data={object_id: object_data}, class_type=class_type, update=update, user_id=user_id,
                    supplier_name_key=supplier_name_key
                )

            __buttons.append(button)

        __buttons.append(GoToBack(new=False))

        return __buttons

    @classmethod
    async def utils_get_or_create_one_button(cls, button_name_key: str, button_data: dict | None = None,
                                             class_type: str | None = None, supplier_name_key: str | None = None,
                                             update: Message | CallbackQuery | None = None,
                                             user_id: int | None = None) -> Any:
        """ Проверяем существует ли объект-кнопка button_name_key в
            какой-либо коллекции если нет создаёт новый объект """
        user_id = user_id if user_id else update.from_user.id

        class_type = class_type.title() if class_type else class_type
        if class_type and class_type not in ['Supplier', 'Feedback']:
            raise ValueError('class_type должен быть Supplier или Feedback')

        button = await cls.button_search_and_action_any_collections(user_id=user_id, action='get',
                                                                    button_name=button_name_key)
        if not button:
            button_data = dict() if not button_data else button_data
            button = await cls.create_button_dynamically(
                data={button_name_key: button_data}, class_type=class_type, update=update, user_id=user_id,
                supplier_name_key=supplier_name_key
            )
        return button
