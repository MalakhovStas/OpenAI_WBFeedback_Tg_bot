import asyncio
import inspect
from os.path import basename

from config import ADMINS, TECH_ADMINS
from loader import bot, logger
from aiogram.types import CallbackQuery, Message


async def get_start_tb_frame_data(exc):
    result = dict()
    start_tb = None
    try:
        next_tb = exc.__traceback__
        while next_tb:
            next_tb = next_tb.tb_next
            if next_tb:
                start_tb = next_tb
        if start_tb:
            frame_list = str(start_tb.tb_frame).split(', ')[1:]
            result['file'] = frame_list[0].split('/')[-1].strip("'")
            result['line'] = frame_list[1].split(' ')[-1]
            result['func'] = frame_list[2].split(' ')[-1].strip('>')
    except Exception:
        result['file'] = 'admins_send_message.py'
        result['func'] = 'get_start_tb_frame_data'
        result['line'] = 'Ошибка получения данных об ошибке из traceback frame'
    return result


async def func_admins_message(update=None, exc=None, message=None, disable_preview_page=None):
    """ Отправляет сообщения об ошибках и состоянии бота администраторам, если их id указаны в
        ADMINS или TECH_ADMINS файла .env """
    try:
        user_name = update.from_user.first_name if update else 'OpenAIManager_line_52'
        user_id = update.from_user.id if update else 'OpenAIManager_line_52'
        update_type = None if not update else update.__class__.__name__
        call_data = update.data if isinstance(update, CallbackQuery) else None
        message_text = update.text if isinstance(update, Message) else None

        if ADMINS or TECH_ADMINS:
            if exc:
                start_exc_data = await get_start_tb_frame_data(exc)
                if message:
                    for admin in TECH_ADMINS:
                        await asyncio.sleep(0.033)
                        await bot.send_message(chat_id=admin, text=message,
                                               disable_web_page_preview=disable_preview_page)
                else:
                    track = inspect.trace()[1] if len(inspect.trace()) > 1 else inspect.trace()[0]
                    file, func, line, code = \
                        basename(track.filename), track.function, track.lineno, "".join(track.code_context)

                    for admin in TECH_ADMINS:
                        await asyncio.sleep(0.033)
                        await bot.send_message(chat_id=admin,
                                               text='&#9888 <b><i>ERROR</i></b> &#9888\n'
                                                    f'<b>User_name</b>:    {user_name}\n'
                                                    f'<b>User_id</b>:    {user_id}\n'
                                                    f'<b>File</b>:    <i>{file}</i>\n'
                                                    f'<b>Func</b>:    <i>{func}</i>\n'
                                                    f'<b>Line</b>:    {line}\n'
                                                    f'<b>Exception</b>:    {exc.__class__.__name__}\n'
                                                    f'<b>Traceback</b>:    {exc}\n'
                                                    f'<b>Code</b>:    {code.strip()}\n\n'
                                                    f'<b>Type</b>:    {update_type}\n'
                                                    f'<b>{"Call" if call_data else "Text"}</b>:    '
                                                    f'{call_data if call_data else message_text}\n'
                                                    f'<b>StartException</b>:\n'
                                                    f' \t \t <b>File</b>: <i>{start_exc_data.get("file")}</i>\n'
                                                    f' \t \t <b>Func</b>: <i>{start_exc_data.get("func")}</i>\n'
                                                    f' \t \t <b>Line</b>: {start_exc_data.get("line")}\n'
                                               )

                        logger.info(f'-> ADMIN SEND MESSAGE -> ERROR -> admin_id: {admin}')

            elif message and exc is None:
                for admin in ADMINS:
                    await asyncio.sleep(0.033)
                    await bot.send_message(chat_id=admin, text=message, disable_web_page_preview=disable_preview_page)
                    logger.info(f'-> ADMIN SEND MESSAGE -> admin_id: {admin}')

    except BaseException as i_exc:
        logger.critical(f'CRITICAL_ERROR(admins_send_message.py): {i_exc}')
