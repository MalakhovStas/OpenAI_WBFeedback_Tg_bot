import re
from typing import Any

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta, timezone


def set_button_name(start_name: str, button_id: str | int) -> tuple[str, str]:
    """ Не асинхронный метод вызывается из __call__ """
    if isinstance(button_id, int):
        button_id = str(button_id)
    long_btn_id = button_id.zfill(7)
    return start_name[:-7] + long_btn_id, long_btn_id


async def check_data(data: str) -> str | None:
    """ Удаляет из строки data все символы из table_symbols на выходе только цифры или None"""
    ru_alphabet = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    en_alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    any_symbols = ' ~`"\'@#№$:;.,%^&?*|()[]{}-=+<>/\\'
    table_symbols = ''.join([*ru_alphabet, *en_alphabet, *any_symbols])

    for sym in table_symbols:
        data = data.replace(sym, '')
    return data if data.isdigit() else None


async def check_notification_time(notif_time: str, user_timezone: str) -> bool:
    result = False
    hours = await check_data(user_timezone)
    tm_zone = timezone(timedelta(hours=int(hours) if hours else 3))
    timezone_now = datetime.now().astimezone(tm_zone)
    if notif_time == 'around_the_clock':
        result = True
    else:
        notif = notif_time.split('-')
        if len(notif) == 2 and all([sym.isdigit() for sym in notif]):
            start, stop = map(int, notif)
            if start <= timezone_now.hour < stop:
                result = True
    # self.logger.info(self.sign + f'check_notif_time {result=} | {notif_time=} | {str(timezone_now)=}')
    return result


async def change_name_button(button, num):
    i_was = None
    res_re = re.search(r'< \d+ >', button.name)
    if res_re:
        i_was = res_re.group(0)
    was = i_was if i_was else '< 0 >'

    will_be = f"< {num} >"
    button.name = button.name.replace(was, will_be)
    return button


async def create_keyboard(button: Any) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text=button.name, callback_data=button.class_name))
    return keyboard


