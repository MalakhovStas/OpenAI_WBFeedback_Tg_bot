from typing import Dict

from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from aiogram.dispatcher.handler import CancelHandler
from config import FLOOD_CONTROL, FLOOD_CONTROL_STOP_TIME
import utils.exception_control
from loader import bot, security, dbase, Base, rdm, logger


class AccessControlMiddleware(BaseMiddleware):
    """ Класс предварительной обработки входящих сообщений для защиты от нежелательной нагрузки """
    dbase = dbase
    bot = bot
    security = security

    def __init__(self) -> None:
        super().__init__()
        self.sign = self.__class__.__name__ + ': '

    @utils.exception_control.exception_handler_wrapper
    async def on_pre_process_update(self, update: Update, update_data: Dict) -> None:
        update = update.message if update.message else update.callback_query
        # print(update)
        # print(update.message.reply_markup.values.get('inline_keyboard')[0][0].text[-7:])
        # print(Base.general_collection)

        user_data = self.manager.storage.data.get(str(update.from_user.id))
        if isinstance(update, CallbackQuery):
            await self.bot.answer_callback_query(callback_query_id=update.id)

        if not await self.security.check_user(update, user_data):
            raise CancelHandler()

        text_last_request = "Message: " + str(update.text) if isinstance(update, Message) else "Callback: " + str(update.data)
        await self.dbase.update_last_request_data(update=update, text_last_request=text_last_request)

        if FLOOD_CONTROL:
            control = await self.security.flood_control(update)
            if control in ['block', 'bad', 'blocked']:
                if control != 'blocked':
                    text = {'block': f'&#129302 Доступ ограничен на {FLOOD_CONTROL_STOP_TIME} секунд',
                            'bad': '&#129302 Не так быстро пожалуйста'}
                    await bot.send_message(chat_id=update.from_user.id, text=text[control])
                raise CancelHandler()
        # data[update.from_user.id] = self.manager.storage.data.get(update.from_user.id)
        import handlers

    @utils.exception_control.exception_handler_wrapper
    async def on_process_update(self, update: Update, update_data: Dict) -> None | Dict:
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_post_process_update(self, update: Update, post: list, update_data: Dict) -> None:
        # with open('data.pickle', 'wb') as f:
        #     pickle.dump(Base.general_collection, f)
        # print(Base.general_collection_dump)
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_pre_process_message(self, message: Message, message_data: Dict) -> None:
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_process_message(self, message: Message, message_data: Dict) -> None:
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_post_process_message(self, message: Message, post: list, message_data: Dict) -> None:
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_pre_process_callback_query(self, call: CallbackQuery, callback_data: Dict) -> None:
        # logger.warning(f'{self.sign} pre_process -> call.data: \033[31m{call.data}\033[0m')
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_process_callback_query(self, call: CallbackQuery, callback_data: Dict) -> None:
        pass

    @utils.exception_control.exception_handler_wrapper
    async def on_post_process_callback_query(self, call: CallbackQuery, post: list, callback_data: Dict) -> None:
        data = callback_data.get('state')
        # prev_button_name = await Base.button_search_and_action_any_collections(
        #     user_id=call.from_user.id, action='get', button_name='previous_button', updates_data=True)

        # print('call.data:', call.data)
        # logger.warning(f'{self.sign} post_process -> call.data: \033[31m{call.data}\033[0m')
        # print('prev_button_name', prev_button_name)

        if not call.data in ['GenerateNewResponseToFeedback', 'DontReplyFeedback', 'UpdateListFeedbacks']:#, 'GoToBack']:
            # and not (call.data.startswith('Feedback') and prev_button_name == 'AnswerManagement'):
            # prev_button_name = await Base.button_search_and_action_any_collections(
            #     user_id=call.from_user.id, action='get', button_name='previous_button', updates_data=True)
            # print('prev_button_name', prev_button_name)

            await data.update_data(previous_button=call.data)
            await Base.button_search_and_action_any_collections(
                user_id=call.from_user.id, action='add',
                button_name='previous_button', instance_button=call.data, updates_data=True)

            # if prev_button_name and not prev_button_name.startswith('Feedback'):
            #     await Base.button_search_and_action_any_collections(
            #         user_id=call.from_user.id, action='add',
            #         button_name='prev2button', instance_button=prev_button_name, updates_data=True)


