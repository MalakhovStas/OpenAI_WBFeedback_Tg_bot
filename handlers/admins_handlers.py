from aiogram.dispatcher import FSMContext
from aiogram.types import Message

from loader import dp, adm, bot
from utils.states import FSMAdminStates


@dp.message_handler(commands=['my_id', 'mailing', 'commands', 'how_users',
                              'stat', 'users_info', 'mailing_admins',
                              'block_user', 'unblock_user', 'change_user_balance',
                              'unloading_logs', 'change_user_requests_balance',
                              'unload_payment_data_user'], state='*')
async def admins_commands_handler(message: Message, state: FSMContext) -> None:
    result, next_state, type_result = await adm.admin_commands(message=message)

    if not result and not type_result:
        return

    await state.set_state(state=next_state) if state else None

    if type_result == 'document':
        await bot.send_document(message.chat.id, result)

    else:
        await bot.send_message(chat_id=message.from_user.id, text=result)


@dp.message_handler(state=FSMAdminStates.password_mailing)
async def admins_in_password_handler(message: Message, state: FSMContext) -> None:
    text, next_state = await adm.in_password(update=message, current_state=await state.get_state())
    await state.set_state(next_state) if next_state else await state.reset_state()
    await bot.send_message(chat_id=message.from_user.id, text=text)


@dp.message_handler(state=FSMAdminStates.mailing_admins, content_types=['text', 'photo', 'audio', 'voice', 'video',
                                                                        'video_note', 'document', 'sticker'])
async def admins_mailing_handler(message: Message, state: FSMContext) -> None:
    text, next_state = await adm.mailing(update=message, only_admins=True)
    await state.set_state(next_state) if next_state else await state.reset_state()
    # await bot.send_message(chat_id=message.from_user.id, text=text)


@dp.message_handler(state=FSMAdminStates.mailing, content_types=['text', 'photo', 'audio', 'voice', 'video',
                                                                 'video_note', 'document', 'sticker'])
async def users_mailing_handler(message: Message, state: FSMContext) -> None:
    text, next_state = await adm.mailing(update=message)
    await state.set_state(next_state) if next_state else await state.reset_state()
    # await bot.send_message(chat_id=message.from_user.id, text=text)


@dp.message_handler(state=[FSMAdminStates.block_user, FSMAdminStates.unblock_user])
async def func_block_unblock_user(message: Message, state: FSMContext):
    """ Обработчик команд блокировки/разблокировки пользователя """
    block = True if await state.get_state() == 'FSMAdminStates:block_user' else False
    text, next_state = await adm.block_unblock_user(user_id=message.text.strip(' '), block=block)

    await state.reset_state() if not next_state else None
    await bot.send_message(chat_id=message.from_user.id, text=text, disable_web_page_preview=True)


@dp.message_handler(state=FSMAdminStates.change_user_balance)
async def func_change_user_balance(message: Message, state: FSMContext):
    """ Обработчик команды изменения баланса пользователя """
    text, next_state = await adm.change_user_balance(data=message.text.split(' '))
    await state.reset_state() if not next_state else None
    await bot.send_message(chat_id=message.from_user.id, text=text, disable_web_page_preview=True)


@dp.message_handler(state=FSMAdminStates.change_user_requests_balance)
async def func_change_user_requests_balance(message: Message, state: FSMContext):
    """ Обработчик команды изменения баланса запросов пользователя """
    text, next_state = await adm.change_user_requests_balance(data=message.text.split(' '))
    await state.reset_state() if not next_state else None
    await bot.send_message(chat_id=message.from_user.id, text=text, disable_web_page_preview=True)


@dp.message_handler(state=FSMAdminStates.unload_payment_data_user)
async def func_change_user_requests_balance(message: Message, state: FSMContext):
    """ Обработчик команды запроса данных об оплатах пользователя """
    result, type_result, next_state = await adm.unload_payments_data_user(user_id=message.text)

    if type_result == 'document':
        await bot.send_document(chat_id=message.from_user.id, document=result)
    else:
        await bot.send_message(chat_id=message.from_user.id, text=result, disable_web_page_preview=True)

    await state.reset_state() if not next_state else None
