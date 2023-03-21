from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.exceptions import MessageToDeleteNotFound
from utils.exception_control import exception_handler_wrapper
from config import BOT_POS, ADVERT_BID_BOT, SCHOOL
from loader import dp, bot, alm, logger, Base


async def delete_message(chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except MessageToDeleteNotFound:
        logger.warning(f'HANDLERS Error: message_id: {message_id} to delete not found in chat_id: {chat_id}')
        return False
    else:
        return True


@dp.message_handler(state='*')
# @exception_handler_wrapper
async def message_any_message(message: Message, state: FSMContext) -> None:
    """ Обработчик сообщений """
    text, keyboard, next_state = await alm.get_reply(update=message, state=state)
    disable_w_p_p = False if text in [ADVERT_BID_BOT, BOT_POS, SCHOOL] else True

    sent_message = await bot.send_message(
        chat_id=message.from_user.id, text=text, reply_markup=keyboard, disable_web_page_preview=disable_w_p_p)

    await state.update_data(last_handler_sent_message_id=sent_message.message_id,
                            last_handler_sent_from_message_message_id=sent_message.message_id)

    Base.updates_data['last_handler_sent_message_id'] = sent_message.message_id
    Base.updates_data['last_handler_sent_from_message_message_id'] = sent_message.message_id

    if next_state:
        await state.set_state(next_state) if next_state != 'reset_state' else await state.reset_state()


@dp.callback_query_handler(lambda callback: callback.data, state='*')
# @exception_handler_wrapper
async def get_call(call: CallbackQuery, state: FSMContext) -> None:
    """ Обработчик обратного вызова """
    text, keyboard, next_state = await alm.get_reply(update=call, state=state)

    await delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    sent_message = await bot.send_message(
        chat_id=call.from_user.id, text=text, reply_markup=keyboard, disable_web_page_preview=True)

    await state.update_data(last_handler_sent_message_id=sent_message.message_id,
                            last_handler_sent_from_call_message_id=sent_message.message_id)

    Base.updates_data['last_handler_sent_message_id'] = sent_message.message_id
    Base.updates_data['last_handler_sent_from_call_message_id'] = sent_message.message_id

    if next_state:
        await state.set_state(next_state) if next_state != 'reset_state' else await state.reset_state()
