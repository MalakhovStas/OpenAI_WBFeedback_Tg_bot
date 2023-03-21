from typing import Any

from aiogram.dispatcher import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from buttons_and_messages.main_menu import MainMenu
from config import ADVERT_BID_BOT, BOT_POS, SCHOOL


class AnswerLogicManager:
    """ Класс Singleton для работы с API Wildberries и соблюдения принципа DRY """
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, bot, ai, logger):
        self.main = MainMenu()
        self.bot = bot
        self.ai = ai
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    async def create_keyboard(self, buttons: list | None, insert: bool = False,
                              main_menu: bool = False, parent_button: Any | None = None) -> InlineKeyboardMarkup:

        # print('AnswerLogicManager -> create_keyboard -> parent_button:', type(parent_button), parent_button)

        parent_button = self.main if not parent_button else parent_button

        # if buttons == self.main.children_buttons:
        #     main_menu = False
        #     insert = True
        #
        # if not parent_button or parent_button == self.main:
        #     insert = True
        #     main_menu = True

        keyboard = InlineKeyboardMarkup()
        if buttons:
            for index, button in enumerate(buttons, 1):
                if button.class_name == 'GoToBack':
                    main_menu = True
                    insert = True

                # align = "left" if button.__class__.__name__.startswith('Feedback') else "center"

                if len(buttons) == 1 or index < len(buttons):
                    if button.class_name == 'EditFeedback':
                        # print('alm EditFeedback:', button)
                        text = f'\n' + (parent_button.any_data.get('answer') if parent_button
                                        and parent_button.any_data else self.main.default_bad_text)
                        keyboard.add(InlineKeyboardButton(text=button.name, switch_inline_query_current_chat=text))
                    else:
                        keyboard.add(
                            InlineKeyboardButton(text=button.name, callback_data=button.callback, url=button.url))
                else:
                    keyboard.insert(
                        InlineKeyboardButton(text=button.name, callback_data=button.callback, url=button.url)) \
                        if insert and not main_menu else keyboard.add(InlineKeyboardButton(
                            text=button.name, callback_data=button.callback, url=button.url))

        if any(button.class_name.startswith('Feedback') for button in buttons):
            keyboard.insert(InlineKeyboardButton(text='🌐 Обновить информацию', callback_data='UpdateListFeedbacks'))

        if main_menu:
            main_inline_button = InlineKeyboardButton(text=self.main.name, callback_data=self.main.callback)
            keyboard.insert(main_inline_button) if insert else keyboard.add(main_inline_button)

        return keyboard

    async def get_reply(self, update: Message | CallbackQuery | None = None, state: FSMContext | None = None,
                        button: Any | None = None, message: Any | None = None, insert: bool = False,
                        main_menu: bool = True) -> tuple[str | None, InlineKeyboardMarkup | None, str | None]:
        buttons = None
        current_data = {}
        current_state = None

        if state:
            current_data = await state.get_data()
            current_state = await state.get_state()

        if isinstance(update, CallbackQuery):
            if button := await self.main.button_search_and_action_any_collections(action='get',
                                                                                  button_name=update.data):
                buttons = button.children_buttons

        elif isinstance(update, Message):
            if update.get_command() == '/start':
                message = None
                button = self.main
                buttons = button.children_buttons

            elif update.get_command() == '/my_shops':
                if button := await self.main.button_search_and_action_any_collections(
                        action='get', button_name='WildberriesCabinet'):
                    buttons = button.children_buttons
                    message = None

            elif update.get_command() == '/add_shops':
                # TODO добавить логику добавления магазина по ID парсинг
                ...
            elif update.get_command() == '/advert_bid_bot':
                return ADVERT_BID_BOT, None, None
            elif update.get_command() == '/bot_pos':
                return BOT_POS, None, None
            elif update.get_command() == '/school':
                return SCHOOL, None, None
            else:
                if message := self.main.message_store.get(current_state):
                    buttons = message.children_buttons

        if not button and not message:
            """ Если нет никаких данных всегда возвращает главное меню например по команде /start"""
            button = self.main
            buttons = button.children_buttons

        if button is self.main:
            # Вывод всех кнопок главного меню
            main_menu = False
            insert = True

        if message:
            main_menu = True
            if hasattr(message.__class__, '_set_answer_logic'):
                reply_text, next_state = await message._set_answer_logic(update, state)
                if hasattr(message, 'children_buttons'):
                    buttons = message.children_buttons
            else:
                reply_text, next_state = message.reply_text, message.next_state

            if reply_text == message.default_incorrect_data_input_text:
                main_menu = False

        else:
            if hasattr(button, 'children_buttons'):
                buttons = button.children_buttons

            if hasattr(button.__class__, '_set_answer_logic'):
                reply_text, next_state = await button._set_answer_logic(update, state)

                if hasattr(button, 'children_buttons'):
                    buttons = button.children_buttons

            else:
                reply_text, next_state = button.reply_text, button.next_state

        # print('AnswerLogicManager -> get_reply -> button:', type(button), button)

        if button.class_name.startswith('Feedback'):
            parent_button = button

        elif button.class_name.startswith('Supplier'):
            parent_button = await self.main.button_search_and_action_any_collections(
                action='get', button_name='WildberriesCabinet')

        elif (button and button.class_name == 'GenerateNewResponseToFeedback') or \
                (message and message.class_name == 'MessageEditFeedbackAnswer'):
            parent_button = await self.main.button_search_and_action_any_collections(
                action='get', button_name=current_data.get('previous_button'))
        else:
            parent_button = None

        # print('AnswerLogicManager -> get_reply -> parent_button:', type(parent_button), parent_button)

        keyboard = await self.create_keyboard(
            buttons=buttons, insert=insert, main_menu=main_menu, parent_button=parent_button)

        return reply_text, keyboard, next_state
