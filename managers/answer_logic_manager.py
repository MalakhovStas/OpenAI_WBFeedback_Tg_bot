from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.dispatcher import FSMContext


from buttons_and_messages.main_menu import MainMenu
from buttons_and_messages.base_classes import BaseMessage, BaseButton


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
                              main_menu: bool = False, parent_button: BaseButton | None = None) -> InlineKeyboardMarkup:

        # if buttons == self.main.children_buttons:
        #     main_menu = False
        #     insert = True
        #
        # if not parent_button or parent_button == self.main:
        #     main_menu = True

        keyboard = InlineKeyboardMarkup()
        if buttons:
            for index, button in enumerate(buttons, 1):
                if button.__class__.__name__ == 'GoToBack':
                    main_menu = True
                    insert = True

                # align = "left" if button.__class__.__name__.startswith('Feedback') else "center"

                if len(buttons) == 1 or index < len(buttons):
                    if button.__class__.__name__ == 'EditFeedback':
                        text = f"\n{parent_button.any_data.get('answer')}" if parent_button else "Ошибка"
                        keyboard.add(InlineKeyboardButton(
                            text=button.name, switch_inline_query_current_chat=text))
                    else:
                        keyboard.add(
                            InlineKeyboardButton(text=button.name, callback_data=button.callback, url=button.url))
                else:
                    keyboard.insert(
                        InlineKeyboardButton(text=button.name, callback_data=button.callback, url=button.url)) \
                        if insert and not main_menu else keyboard.add(InlineKeyboardButton(
                            text=button.name, callback_data=button.callback, url=button.url))

        # if buttons != self.main.children_buttons:
        #     back_inline_button = InlineKeyboardButton(text='◀ Назад', callback_data='GoToBack')
        #     keyboard.add(back_inline_button)  # if main_menu else keyboard.insert(back_inline_button)
        #     insert = True
        #

        # print('create_keyboard - parent_button:', parent_button)
        # print('create_keyboard - buttons:', buttons)
        if any(button.__class__.__name__.startswith('Feedback') for button in buttons):
        # if parent_button.__class__.__name__.startswith('Supplier'):
            main_inline_button = InlineKeyboardButton(
                text='🌐 Обновить информацию', callback_data='UpdateListFeedbacks')
            keyboard.insert(main_inline_button)

        if main_menu:
            main_inline_button = InlineKeyboardButton(text=self.main.name, callback_data=self.main.callback)
            keyboard.insert(main_inline_button) if insert else keyboard.add(main_inline_button)

        return keyboard

    async def get_reply(self, update: Message | CallbackQuery = None, state: FSMContext | None = None,
                        button: BaseButton | None = None, message: BaseMessage | None = None,
                        insert: bool = False, main_menu: bool = True
                        ) -> tuple[str | None, InlineKeyboardMarkup | None, str | None]:
        buttons = None

        if isinstance(update, CallbackQuery):
            if button := await self.main.button_search_and_action_any_collections(action='get', button_name=update.data):
                buttons = button.children_buttons
        else:
            if update.get_command() == '/start':
                message = None
                button = self.main
                buttons = button.children_buttons
            else:
                if message := self.main.message_store.get(await state.get_state()):
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
            if hasattr(button.__class__, '_set_answer_logic'):
                reply_text, next_state = await button._set_answer_logic(update, state)
                if hasattr(button, 'children_buttons'):
                    buttons = button.children_buttons
            else:
                reply_text, next_state = button.reply_text, button.next_state

        # if button.__class__.__name__.startswith('Feedback'):
        #     if reply_text.endswith(BaseButton.default_generate_answer):
        #         reply_text = await self.reply_feedback_button(button=button, reply_text=reply_text, update=update)
        #     else:
                # reply_text = button.reply_text + f"<code>{button.any_data.get('answer')}</code>"

        if button.__class__.__name__.startswith('Feedback'):
            parent_button = button

        elif button.__class__.__name__ == 'GenerateNewResponseToFeedback' or \
                message.__class__.__name__ == 'MessageEditFeedbackAnswer':

            current_data = await state.get_data()
            parent_button = await self.main.button_search_and_action_any_collections(
                action='get', button_name=current_data.get('previous_button'))

        else:
            parent_button = None

        keyboard = await self.create_keyboard(
            buttons=buttons, insert=insert, main_menu=main_menu, parent_button=parent_button)

        return reply_text, keyboard, next_state
