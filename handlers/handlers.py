from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message, ParseMode
from aiogram.utils.exceptions import MessageToDeleteNotFound, MessageCantBeDeleted, \
    MessageToEditNotFound, MessageCantBeEdited
from utils.exception_control import exception_handler_wrapper
from config import BOT_POS, ADVERT_BID_BOT, SCHOOL
from loader import dp, bot, alm, logger, Base


async def delete_message(chat_id, message_id):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except (MessageToDeleteNotFound, MessageCantBeDeleted) as exc:
        logger.warning(f'HANDLERS Error: {chat_id=} | {message_id=} | {exc=}')
        return False
    else:
        return True


async def edit_message(chat_id, message_id):
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id)
    except (MessageToEditNotFound, MessageCantBeEdited) as exc:
        logger.warning(f'HANDLERS Error: {chat_id=} | {message_id=} | {exc=}')
        return False
    else:
        return True


@dp.message_handler(state='*')
@exception_handler_wrapper
async def get_message_handler(message: Message, state: FSMContext) -> None:
    """ Обработчик сообщений """
    reply_text, keyboard, next_state = await alm.get_reply(update=message, state=state)
    disable_w_p_p = False if reply_text in [ADVERT_BID_BOT, BOT_POS, SCHOOL] else True

    if last_handler_sent_message_id := await Base.button_search_and_action_any_collections(
            user_id=message.from_user.id, action='get', button_name='last_handler_sent_message_id', updates_data=True):

        if await state.get_state() in ['FSMMainMenuStates:create_response_manually',
                                       'FSMMainMenuStates:submit_for_revision_task_response_manually']:
            await edit_message(chat_id=message.from_user.id, message_id=last_handler_sent_message_id)
        else:
            await delete_message(chat_id=message.from_user.id, message_id=last_handler_sent_message_id)

    if reply_text.strip().endswith(':ai:some_question'):
        reply_text = reply_text.rstrip(':ai:some_question')
        bot.parse_mode = None

    sent_message = await bot.send_message(chat_id=message.from_user.id, text=reply_text,
                                          reply_markup=keyboard, disable_web_page_preview=disable_w_p_p)
    bot.parse_mode = ParseMode.HTML

    await state.update_data(last_handler_sent_message_id=sent_message.message_id,
                            last_handler_sent_from_message_message_id=sent_message.message_id)

    # Base.updates_data['last_handler_sent_message_id'] = sent_message.message_id
    await Base.button_search_and_action_any_collections(
        user_id=message.from_user.id, action='add', button_name='last_handler_sent_message_id',
        updates_data=True, instance_button=sent_message.message_id)
    # Base.updates_data['last_handler_sent_from_message_message_id'] = sent_message.message_id
    await Base.button_search_and_action_any_collections(
        user_id=message.from_user.id, action='add', button_name='last_handler_sent_from_message_message_id',
        updates_data=True, instance_button=sent_message.message_id)

    if next_state:
        await state.set_state(next_state) if next_state != 'reset_state' else await state.reset_state()

        await Base.button_search_and_action_any_collections(
            user_id=message.from_user.id, action='add', button_name='state', updates_data=True,
            instance_button=next_state if next_state != 'reset_state' else None
        )


@dp.callback_query_handler(lambda callback: callback.data, state='*')
@exception_handler_wrapper
async def get_call_handler(call: CallbackQuery, state: FSMContext) -> None:
    """ Обработчик обратного вызова """
    reply_text, keyboard, next_state = await alm.get_reply(update=call, state=state)

    if call.data in ['CreateNewTaskForResponseManually',
                     'SubmitForRevisionTaskResponseManually', 'RegenerateAIResponse']:
        await edit_message(chat_id=call.from_user.id, message_id=call.message.message_id)
    else:
        await delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    if reply_text.strip().endswith(':ai:some_question'):
        reply_text = reply_text.rstrip(':ai:some_question')
        bot.parse_mode = None

    sent_message = await bot.send_message(chat_id=call.from_user.id, text=reply_text,
                                          reply_markup=keyboard, disable_web_page_preview=True)
    bot.parse_mode = ParseMode.HTML

    await state.update_data(last_handler_sent_message_id=sent_message.message_id,
                            last_handler_sent_from_call_message_id=sent_message.message_id)

    # Base.updates_data['last_handler_sent_message_id'] = sent_message.message_id
    await Base.button_search_and_action_any_collections(
        user_id=call.from_user.id, action='add', button_name='last_handler_sent_message_id',
        updates_data=True, instance_button=sent_message.message_id)
    # Base.updates_data['last_handler_sent_from_call_message_id'] = sent_message.message_id
    await Base.button_search_and_action_any_collections(
        user_id=call.from_user.id, action='add', button_name='last_handler_sent_from_call_message_id',
        updates_data=True, instance_button=sent_message.message_id)

    if next_state:
        await state.set_state(next_state) if next_state != 'reset_state' else await state.reset_state()

        await Base.button_search_and_action_any_collections(
            user_id=call.from_user.id, action='add', button_name='state', updates_data=True,
            instance_button=next_state if next_state != 'reset_state' else None
        )
