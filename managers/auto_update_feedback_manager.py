import time
from datetime import datetime, timedelta

from aiogram.contrib.fsm_storage.memory import MemoryStorage

from buttons_and_messages.base_classes import Utils, Base, DefaultButtonForAUFMGoToFeed
from config import FACE_BOT, MODE_GENERATE_ANSWER, AUFM_ONLY_DATE, NUM_FEED_BUTTONS
from utils import misc_utils


class AutoUpdateFeedbackManager:
    """ Класс Singleton для автоматического поиска новых отзывов в
    заданном интервале __interval и уведомлений о них"""
    __instance = None
    __default_answer_button = DefaultButtonForAUFMGoToFeed()

    if MODE_GENERATE_ANSWER == 'automatic':
        __default_suffix = FACE_BOT + 'В вашем магазине\n<b>{supplier_title}</b>\nпоявился новый отзыв, ' \
                                      'я сгенерировал ответ:\n\n'
    else:
        __default_suffix = FACE_BOT + 'В вашем магазине\n<b>{supplier_title}</b>\nпоявился новый отзыв:\n\n'

    base = Base
    base_utils = Utils
    m_utils = misc_utils

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, dbase, storage, bot, wb_api, wb_parsing, alm, logger):
        self.dbase = dbase
        self.storage: MemoryStorage = storage
        self.bot = bot
        self.wb_api = wb_api
        self.wb_parsing = wb_parsing
        self.alm = alm
        self.logger = logger
        self.sign = self.__class__.__name__ + ': '

    async def finding_unanswered_feedbacks(self):
        """ Выбирает всех пользователей из БД -> если у пользователя есть suppliers -> находит или создает
            класс кнопку Supplier+supplier_id """
        start_time = time.time()
        total_suppliers = 0
        total_found_new_unanswered_feedbacks = 0
        wb_users = await self.dbase.select_all_wb_users()
        self.logger.info(self.sign + f'\033[31mSTART LOOKING FEEDBACKS\033[0m -> num users:{len(wb_users)}')

        for wb_user in wb_users:
            if not await self.m_utils.check_notification_time(notif_time=wb_user.notification_times,
                                                              user_timezone=wb_user.timezone_notification_times):
                continue

            wb_user_id = wb_user.WB_user_id
            user_id = wb_user.user_id
            seller_token = wb_user.sellerToken
            wb_user_suppliers = wb_user.suppliers if wb_user.suppliers else dict()

            self.logger.debug(self.sign + f'{wb_user_id=} | TG_{user_id=} | {wb_user_suppliers=}')

            for supplier_name_key, supplier_data in wb_user_suppliers.items():

                total_suppliers += 1
                supplier_button = await self.base_utils.utils_get_or_create_one_button(
                    user_id=user_id, button_name_key=supplier_name_key,
                    button_data=supplier_data, class_type='Supplier'
                )

                if supplier_name_key.startswith('SupplierParsing'):
                    feedbacks, supplier_total_feeds = await self.wb_parsing(supplier_id=supplier_name_key,
                                                                            user_id=user_id, waiting_msgs=False,
                                                                            only_date=AUFM_ONLY_DATE)
                else:
                    feedbacks, supplier_total_feeds = await self.wb_api.get_feedback_list(seller_token=seller_token,
                                                                                          supplier=supplier_name_key,
                                                                                          user_id=user_id,
                                                                                          only_date=AUFM_ONLY_DATE)
                if feedbacks:
                    buttons = await self.base_utils.utils_get_or_create_buttons(
                        collection=feedbacks, class_type='Feedback',
                        supplier_name_key=supplier_name_key, user_id=user_id
                    )

                    for button in buttons:
                        if button.class_name == 'GoToBack':
                            continue

                        total_found_new_unanswered_feedbacks += 1

                        text, keyboard, next_state = await self.alm.get_reply(button=button, not_keyboard=True)

                        btn_goto_feed = await self.__default_answer_button(user_id=user_id, feedback_button=button)

                        """К каждому сообщению создаёт кнопку перейти к отзыву -> DefaultButtonForAUFM"""
                        keyboard = await self.m_utils.create_keyboard(btn_goto_feed)

                        if MODE_GENERATE_ANSWER == 'manual':
                            text = text.split('<b>Ответ:</b>\n')[0]

                        text = self.__default_suffix.format(supplier_title=supplier_data.get('button_name')) + text
                        await self.bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard,
                                                    disable_web_page_preview=True)
                    if supplier_button:
                        await self.base.m_utils.change_name_button(button=supplier_button, num=supplier_total_feeds)

                        for button in buttons:
                            if button.class_name == 'GoToBack' or len(supplier_button.children_buttons) > NUM_FEED_BUTTONS:
                                break
                            else:
                                supplier_button.children_buttons.insert(-1, button)


                        # [supplier_button.children_buttons.insert(-1, button) for button in buttons if button.class_name != 'GotoBack']
                        # supplier_button.children_buttons = \
                        #     [*supplier_button.children_buttons, *buttons][:NUM_FEED_BUTTONS]

        spent_time = (datetime.utcfromtimestamp(0) + timedelta(seconds=time.time() - start_time)).strftime('%H:%M:%S')
        self.logger.info(self.sign + f'\033[31mFINISHED\033[0m -> {len(wb_users)} | {total_suppliers=} | '
                                     f'{total_found_new_unanswered_feedbacks=} | {spent_time=}')


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
"""
