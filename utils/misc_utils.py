import re
from random import choice
from typing import Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta, timezone
from config import NUM_FEEDS_ON_SUPPLIER_BUTTON, DEFAULT_FEED_ANSWER


def set_button_name(button_id: str | int) -> str:
    """ Не асинхронный метод вызывается из __call__ """
    if isinstance(button_id, int):
        button_id = str(button_id)

    #long_btn_id -> 0000058
    long_btn_id = button_id.zfill(7)
    # return start_name[:-7] + long_btn_id, long_btn_id
    return long_btn_id


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
    # self.logger.debug(self.sign + f'check_notif_time {result=} | {notif_time=} | {str(timezone_now)=}')
    return result


async def change_name_button(button, num: int | None = None, minus_one: bool = False):
    """ Изначальное имя кнопки задаётся тут ->  buttons_and_messages/base_classes.py:979 """
    i_was = None
    res_re = re.search(r'〔 \d+ 〕', button.name)
    if res_re:
        i_was = res_re.group(0)
    was = i_was if i_was else '〔 0 〕'

    if minus_one:
        num = int(was.strip('〔〕 '))-1

    if NUM_FEEDS_ON_SUPPLIER_BUTTON == '99+':
        button.name = button.name.replace(was, f'〔 {NUM_FEEDS_ON_SUPPLIER_BUTTON} 〕') if num > 99 \
            else button.name.replace(was, f'〔 {num} 〕')
    else:
        button.name = button.name.replace(was, f'〔 {num} 〕')
    return button


async def create_keyboard(button: Any) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text=button.name, callback_data=button.class_name))
    return keyboard


async def reversed_date_time_feedback(object_data):
    dt, tm = object_data.get("createdDate")[:16].split("T")
    dt_tm = ' '.join(('-'.join(dt.split('-')[::-1]), tm))
    return dt_tm


async def random_choice_dict_elements(is_dict: dict, num_elements: int) -> dict:
    result_dict = dict()
    if len(is_dict) > num_elements:
        while len(result_dict) < num_elements:
            key = choice(list(is_dict.keys()))
            result_dict.update({key: is_dict[key]})
    else:
        result_dict = is_dict
    return result_dict


async def set_hint_in_answer_for_many_feeds(feedbacks: dict) -> dict:
    from config import DEFAULT_FEED_ANSWER
    [feed_data.update(answer=DEFAULT_FEED_ANSWER) for feed_name, feed_data in feedbacks.items()]
    return feedbacks


async def set_reply_text_to_feed(feed, new_object: bool = False):
    if new_object:
        answer = feed.get("answer") if feed.get("answer") == DEFAULT_FEED_ANSWER \
            else f'<code>{feed.get("answer")}</code>'
        return answer

    else:
        answer = feed.any_data.get('answer') if feed.any_data.get('answer') == DEFAULT_FEED_ANSWER \
            else f"<code>{feed.any_data.get('answer')}</code>"

        new_reply_text = feed.reply_text.split('<b>Ответ:</b>\n')[0] + '<b>Ответ:</b>\n' + answer

        return new_reply_text
