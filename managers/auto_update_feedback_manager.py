import time
from datetime import datetime, timedelta, timezone

# from utils.exception_control import exception_handler_wrapper
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from buttons_and_messages.base_classes import Utils, DefaultButtonForAUFM
from config import FACE_BOT
from utils import misc_utils


class AutoUpdateFeedbackManager:
    """ Класс Singleton для автоматического поиска новых отзывов в
    заданном интервале __interval и уведомлений о них"""
    __instance = None
    # __default_answer_button = DefaultButtonForAUFM()

    __default_suffix = FACE_BOT + 'В вашем магазине\n <b>{supplier_title}</b> \n' \
                                  'появился новый отзыв, я сгенерировал ответ:\n\n'
    m_utils = misc_utils

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, dbase, storage, bot, wb_api, alm, base, scheduler, logger):
        self.dbase = dbase
        self.storage: MemoryStorage = storage
        self.bot = bot
        self.wb_api = wb_api
        self.alm = alm
        self.base = base
        self.scheduler = scheduler
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    async def finding_unanswered_feedbacks(self):
        start_time = time.time()
        total_suppliers = 0
        total_found_new_unanswered_feedbacks = 0
        wb_users = self.dbase.select_all_wb_users()
        self.logger.info(self.sign + f'i start looking -> finding_unanswered_feedbacks -> num users:{len(wb_users)}')

        for wb_user in wb_users:
            if not await self.m_utils.check_notification_time(notif_time=wb_user.notification_times,
                                                              user_timezone=wb_user.timezone_notification_times):
                continue

            seller_token = wb_user.sellerToken
            user_id = wb_user.user_id

            self.logger.debug(f'{wb_user=} | TG_{user_id=} | {wb_user.suppliers=}')

            for supplier_name_key, supplier_data in wb_user.suppliers.items():
                total_suppliers += 1
                # self.logger.debug(f'{supplier_name_key=}')
                feedbacks, supplier_total_feeds = await self.wb_api.get_feedback_list(
                    seller_token=seller_token, supplier=supplier_name_key, user_id=user_id)

                # self.logger.debug(f'{feedbacks=}')
                if feedbacks:
                    buttons = await Utils.utils_get_or_create_buttons(
                        collection=feedbacks, class_type='feedback',
                        supplier_name_key=supplier_name_key, user_id=user_id
                    )
                    # self.logger.debug(f'{buttons=}')

                    for button in buttons:
                        if button.__class__.__name__ == 'GoToBack':
                            continue

                        total_found_new_unanswered_feedbacks += 1
                        # self.logger.error(f'{button=}')

                        text, keyboard, next_state = await self.alm.get_reply(button=button)
                        # print(button)
                        # print(button.button_id)
                        # print(button.__class__.__name__)
                        # btn_goto_feed = self.__default_answer_button(feed_id=button.button_id,
                        #                                              feed_key_name=button.__class__.__name__)
                        # keyboard = await self.create_keyboard(btn_goto_feed)

                        text = self.__default_suffix.format(supplier_title=supplier_data.get('button_name')) + text
                        # await self.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard,
                        #                             disable_web_page_preview=True)
                        await self.bot.send_message(chat_id=user_id, text=text, disable_web_page_preview=True)


                    supplier_btn = await self.base.button_search_and_action_any_collections(
                        'get', button_name=supplier_name_key)
                    await self.base.m_utils.change_name_button(supplier_btn, supplier_total_feeds)

                        # TODO Придумать как работать с кнопками
                        # await self.storage.update_data(chat=user_id, user=user_id,
                        #                                data={'AUFManager_button': button.__class__.__name__})
                        # print(await self.storage.get_data(chat=user_id, user=user_id))
        # print(self.storage.data)

        spent_time = (datetime.utcfromtimestamp(0) + timedelta(seconds=time.time() - start_time)).strftime('%H:%M:%S')
        self.logger.info(self.sign + f'finished -> finding_unanswered_feedbacks -> total_users: {len(wb_users)} | '
                                     f'{total_suppliers=} | {total_found_new_unanswered_feedbacks=} | {spent_time=}')
        # self.scheduler.resume()


"""
{
    "Feedback3CxY9oYBQBfka8TNgTiy": {
        "answer": "Спасибо за ваш отзыв! Мы рады, что вам понравилось. Будем рады видеть вас снова!",
        "button_name": "[ 5 ]  Однозначно 5*",
        "createdDate": "2023-03-18T20:10:41Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Однозначно 5*"
    },
    "Feedback5HRe84YBk9xzjhYZAeGy": {
        "answer": "Спасибо за ваш отзыв! Мы рады, что вам понравилась наша кожанка. Мы постарались сделать ее легкой и комфортной, чтобы вы могли носить ее с комфортом. Мы рады, что вы выбрали размер М, чтобы быть более свободной.",
        "button_name": "[ 5 ]  Не люблю толстые и тяжелые кожанки , эта огонь ! Ношу S , Взяла М , что бы была более свободная )",
        "createdDate": "2023-03-18T06:17:50Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Не люблю толстые и тяжелые кожанки , эта огонь ! Ношу S , Взяла М , что бы была более свободная )"
    },
    "Feedback5Hb7-IYBv9_TjX_mQvv4": {
        "answer": "ла про примерку в магазине.\n\nСпасибо за Ваш отзыв. Приносим извинения за неудобства. Мы понимаем, что примерка в магазине могла бы помочь Вам выбрать подходящий размер. Предлагаем Вам вернуть пуховик и получить замену или возврат денег. Пожалуйста, свяжитесь с нами, чтобы обсудить дальнейшие действия.",
        "button_name": "[ 5 ]  Здравствуйте. Пуховик был красивым ,ткань качественная, не подошёл по длине. Мерила его дома  , забы",
        "createdDate": "2023-03-19T08:27:42Z",
        "productName": "Пуховик пальто куртка зимняя",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Здравствуйте. Пуховик был красивым ,ткань качественная, не подошёл по длине. Мерила его дома  , забыла положить  пояс. Как переслать его вам? Обратилась в пвз. Сказали написать вам."
    },
    "FeedbackCXio8oYBc4LImbbGRQEy": {
        "answer": ".\n\nСпасибо за ваш положительный отзыв! Мы рады, что вам понравилась наша куртка. Мы постарались сделать ее максимально комфортной и стильной. Будем рады видеть вас снова!",
        "button_name": "[ 5 ]  Куртка кайф! Мягчайшая и стильная",
        "createdDate": "2023-03-18T02:59:19Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Куртка кайф! Мягчайшая и стильная"
    },
    "FeedbackCjcA84YBfnpWqlBeuml5": {
        "answer": "ой\n\nСпасибо за Ваш отзыв! Мы рады, что Вам понравилось качество и фитинг дивана. По поводу топорщины спинки, мы постараемся улучшить дизайн для большего комфорта. Спасибо за Ваше внимание!",
        "button_name": "[ 5 ]  Очень понравилось как сидит,качество хорошее,нитки не торчат. Спинка топорщится потому что фасон так",
        "createdDate": "2023-03-18T04:35:57Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Очень понравилось как сидит,качество хорошее,нитки не торчат. Спинка топорщится потому что фасон такой,мне нравится"
    },
    "FeedbackE3Zh94YBv9_TjX_mOYJE": {
        "answer": "Спасибо за ваш отзыв. Мы очень ценим ваше мнение. Приносим извинения за неудобства, вызванные вами. Мы постараемся улучшить наш сервис и продукцию для более приятного покупательского опыта.",
        "button_name": "[ 5 ]  Куртка отличный,заказала 2 куртки,но эту куртку отдала обратно .",
        "createdDate": "2023-03-19T00:59:49Z",
        "productName": "Куртка весенняя короткая",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Куртка отличный,заказала 2 куртки,но эту куртку отдала обратно ."
    },
    "FeedbackHJ0B84YBJ99b87NGE2qE": {
        "answer": "Спасибо за ваш отзыв! Мы рады, что вы нашли именно то, что вам нужно. Мы постоянно стремимся предоставлять нашим клиентам высококачественные изделия из натуральной кожи.",
        "button_name": "[ 5 ]  Выбор пал именно на нее, подошла по размеру, кожа у нее не слишком тонкая.",
        "createdDate": "2023-03-18T04:36:19Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Выбор пал именно на нее, подошла по размеру, кожа у нее не слишком тонкая."
    },
    "FeedbackIHQt64YBc4LImbbG3ef5": {
        "answer": "атриваться\n\nСпасибо за Ваш отзыв. Мы рады, что Вам понравилась наша продукция. Мы постараемся улучшить качество наших изделий, чтобы исправить недостатки. Спасибо за Ваше внимание.",
        "button_name": "[ 4 ]  Хорошо сидит,не стала делать возврат есть один минус ,внутри в капюшоне, но не заметно если не присм",
        "createdDate": "2023-03-16T16:08:17Z",
        "productName": "Куртка весенняя с капюшоном",
        "productValuation": 4,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Хорошо сидит,не стала делать возврат есть один минус ,внутри в капюшоне, но не заметно если не присматриваться"
    },
    "FeedbackTqEf74YBbskpjQp27Jrm": {
        "answer": ".\n\nПриносим извинения за неудобства. Мы постараемся улучшить нашу продукцию, чтобы она была более подходящей для вас. Пожалуйста, проверьте наш ассортимент и приобретайте то, что вам нравится.",
        "button_name": "[ 4 ]  Ждала эту куртку,была уверена,что подойдет.\nНо не выкупила.На мой 46р чуть большевата,но не критично",
        "createdDate": "2023-03-17T10:31:32Z",
        "productName": "Куртка весенняя короткая",
        "productValuation": 4,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Ждала эту куртку,была уверена,что подойдет.\nНо не выкупила.На мой 46р чуть большевата,но не критично.Есть не закрепленные концы строчек.\nПонравилось как смотрится с переди.Разрезы по бокам смотрятся как-то  несуразно.Под куртку надо надевать что-то укороченное,чтобы не было видно  в разрезах.\nРазрезы обработаны не аккуратно,лежат волной,что портит весь вид.Если бы не разрезы,взяла бы."
    },
    "FeedbackgBg59IYBQOOSTxXoqWhZ": {
        "answer": " размеру идеально подошла.\n\nСпасибо за ваш отзыв! Мы рады, что вам понравилась наша куртка и что она подошла по размеру. Мы постоянно стремимся предоставлять нашим клиентам высококачественные товары и отличный сервис. Спасибо, что вы выбрали нас!",
        "button_name": "[ 5 ]  Куртка отличного качества!не тонкая, пришла не мятая и без запаха! Без брака. На рост 180 взяла М по",
        "createdDate": "2023-03-18T10:17:45Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Куртка отличного качества!не тонкая, пришла не мятая и без запаха! Без брака. На рост 180 взяла М по рукам длина отлично! Попу прикрывает на половину, в спине не топырщется ! За свою цену шик"
    },
    "FeedbackhXeW-YYBv9_TjX_mwlAa": {
        "answer": "Спасибо за ваш положительный отзыв! Мы рады, что вам понравилась наша куртка. Мы постоянно стремимся предлагать вам лучшие качественные товары и услуги. Спасибо за вашу поддержку!",
        "button_name": "[ 5 ]  Куртка огонь и в пир и в мир.",
        "createdDate": "2023-03-19T11:17:32Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Куртка огонь и в пир и в мир."
    },
    "FeedbackjEGO74YBT-IFIyX_YxCU": {
        "answer": "рублей очень даже достойно.\n\nОтлично! Рады, что вам понравилась наша куртка. Мы стараемся предлагать качественные и привлекательные товары по доступным ценам. Спасибо за ваш отзыв!",
        "button_name": "[ 5 ]  Классная куртка 🤪 на рост 165см брала размер M, всё подошло, запаха нет, материал приятный, за 1900 ",
        "createdDate": "2023-03-17T12:32:12Z",
        "productName": "Косуха кожаная куртка короткая oversize",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Классная куртка 🤪 на рост 165см брала размер M, всё подошло, запаха нет, материал приятный, за 1900 куртка супер! 💗"
    },
    "FeedbackkEKF84YBT-IFIyX_bocT": {
        "answer": "Спасибо за Ваш отзыв! Мы рады, что Вам понравилась наша куртка. Мы постарались сделать ее максимально комфортной и удобной. Мы рады, что Вы угадали размер.",
        "button_name": "[ 5 ]  Куртка класс, ношу 50 размер, взяла 52 с размером угадала",
        "createdDate": "2023-03-18T07:00:53Z",
        "productName": "Куртка весенняя с капюшоном",
        "productValuation": 5,
        "supplier": "Supplier727553e6-1c20-45af-8f93-031dac28cb1e",
        "text": "Куртка класс, ношу 50 размер, взяла 52 с размером угадала"
    }
}
"""
