import re

from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from buttons_and_messages.time_zones import MoscowUtcUp3, KaliningradUtcUp2, SamaraUtcUp4, EkaterinburgAndAktauUtcUp5, \
    OmskAndNurSultanUtcUp6, KrasnoyarskUtcUp7, IrkutskUtcUp8, YakutskUtcUp9, VladivostokUtcUp10, MagadanUtcUp11, \
    KamchatkaUtcUp12
from config import BOT_NIKNAME, WB_TAKE
from utils.states import FSMPersonalCabinetStates, FSMUtilsStates
from .base_classes import Base, BaseButton, BaseMessage

timezones = [KaliningradUtcUp2(),
             MoscowUtcUp3(),
             SamaraUtcUp4(),
             EkaterinburgAndAktauUtcUp5(),
             OmskAndNurSultanUtcUp6(),
             KrasnoyarskUtcUp7(),
             IrkutskUtcUp8(),
             YakutskUtcUp9(),
             VladivostokUtcUp10(),
             MagadanUtcUp11(),
             KamchatkaUtcUp12()]


""" Объекты без родителей """
# Au7n8BPw0O7ADPCM2MEMQh1PfoKMeTuH7CT-Pnn-_eIHretpsewN14c9_5RyptC0DYc7ttIvfxBTYkcDfzyhNoe2Vq_haFr4MksJ8LKogBwrtA


class GoToBack(BaseButton):
    def _set_name(self) -> str:
        return '◀ Назад'

    async def _set_answer_logic(self, update, state):
        data = await state.get_data()
        result_button = await self.button_search_and_action_any_collections(action='get', button_name='PersonalCabinet')

        if prev_button := await self.button_search_and_action_any_collections(action='get', button_name=data.get('previous_button')):
            if parent_prev_button := await self.button_search_and_action_any_collections(action='get', button_name=prev_button.parent_name):
                result_button = parent_prev_button

        if hasattr(result_button.__class__, '_set_answer_logic'):
            reply_text, next_state = await result_button._set_answer_logic(update, state)
        else:
            reply_text, next_state = result_button.reply_text, result_button.next_state

        self.children_buttons = result_button.children_buttons
        return reply_text, next_state


class PostFeedback(BaseButton):
    def _set_name(self) -> str:
        return '📩 Опубликовать'

    async def _set_answer_logic(self, update, state):
        data = await state.get_data()
        feed_button = await self.button_search_and_action_any_collections(
            action='get', button_name=data.get('previous_button'))

        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                wb_user.unanswered_feedbacks.pop(feed_button.__class__.__name__)
                seller_token = wb_user.sellerToken
                signature = wb_user.signature_to_answer
                wb_user.save()

        # print(seller_token)
        # print(feed_button.parent_name.lstrip('Supplier'))
        # print(feed_button.__class__.__name__.lstrip('Feedback'))
        # print(feed_button.any_data.get('answer'))

        feedback_answer_text = feed_button.any_data.get('answer')
        if signature:
            feedback_answer_text += f"\n\n{signature}"

        result = await self.wb_api.send_feedback(
            seller_token=seller_token,
            x_supplier_id=feed_button.parent_name.lstrip('Supplier'),
            feedback_id=feed_button.__class__.__name__.lstrip('Feedback'),
            feedback_answer__text=feedback_answer_text,
            update=update
        )

        await self.button_search_and_action_any_collections(action='pop', instance_button=feed_button)

        supplier_button = await self.button_search_and_action_any_collections(
            action='get', button_name=feed_button.parent_name)

        supplier_button.children_buttons.remove(feed_button)

        was = re.search(r'< \d+ >', supplier_button.name).group(0)
        will_be = f"< {int(was.strip('<> ')) - 1} >"
        supplier_button.name = supplier_button.name.replace(was, will_be)

        self.children_buttons = supplier_button.children_buttons
        return supplier_button.reply_text, supplier_button.next_state


class EditFeedback(BaseButton):
    def _set_name(self) -> str:
        return '✏ Редактировать'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)

        data = await state.get_data()
        # previous_button = self.feedback_collection.get(data.get('previous_button'))

        previous_button = await self.button_search_and_action_any_collections(
            action='get', button_name=data.get('previous_button'))

        reply_text = previous_button.any_data.get('answer')
        self.reply_text = reply_text

        return self.reply_text, self.next_state


class GenerateNewResponseToFeedback(BaseButton):
    def _set_name(self) -> str:
        return '✍ Сгенерировать новый ответ'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)
        message_waiting = await self.bot.send_message(chat_id=update.from_user.id, text=self.default_generate_answer)

        data = await state.get_data()

        # previous_button = self.feedback_collection.get(data.get('previous_button'))
        previous_button = await self.button_search_and_action_any_collections(action='get', button_name=data.get('previous_button'))

        reply_feedback = await self.ai.reply_feedback(previous_button.any_data.get('text'))
        previous_button.any_data['answer'] = reply_feedback

        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                if wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__):
                    wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__).update({'answer': reply_feedback})
                    wb_user.save()

        self.children_buttons = previous_button.children_buttons
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=message_waiting.message_id)

        # return previous_button.reply_text + f"<code>{previous_button.any_data.get('answer')}</code>", self.next_state

        new_reply_text = previous_button.reply_text.split('<b>Ответ:</b>\n\n')[0] + \
            '<b>Ответ:</b>\n\n'+f"<code>{previous_button.any_data.get('answer')}</code>"
        return new_reply_text, self.next_state


class DontReplyFeedback(BaseButton):
    def _set_name(self) -> str:
        return '⛔ Не отвечать на отзыв'

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        data = await state.get_data()
        # removed_button = self.feedback_collection.pop(data.get('previous_button'), None)
        removed_button = await self.button_search_and_action_any_collections(action='pop', button_name=data.get('previous_button'))

        # supplier_button = self.supplier_collection.get(removed_button.parent_name)
        supplier_button = await self.button_search_and_action_any_collections(action='get', button_name=removed_button.parent_name)

        supplier_button.children_buttons.remove(removed_button)
        self.children_buttons = supplier_button.children_buttons
        await self.change_name_button(supplier_button, len(self.children_buttons)-1)

        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                if rm_feed := wb_user.unanswered_feedbacks.pop(removed_button.__class__.__name__, None):
                    wb_user.ignored_feedbacks[removed_button.__class__.__name__] = rm_feed
                    wb_user.save()

        return supplier_button.reply_text, supplier_button.next_state


class MessageEditFeedbackAnswer(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:edit_feedback_answer'

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        data = await state.get_data()
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message_id)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=data.get('last_handler_sent_message_id'))

        # previous_button = self.feedback_collection.get(data.get('previous_button'))
        previous_button = await self.button_search_and_action_any_collections(action='get', button_name=data.get('previous_button'))

        new_reply_text = update.text.replace(f'@{BOT_NIKNAME}', '').strip().strip('\n').strip()
        previous_button.any_data['answer'] = new_reply_text

        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                if wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__):
                    wb_user.unanswered_feedbacks.get(previous_button.__class__.__name__).update({'answer': new_reply_text})
                    wb_user.save()

        self.children_buttons = previous_button.children_buttons

        # return previous_button.reply_text + f"<code>{previous_button.any_data.get('answer')}</code>", self.next_state
        new_reply_text = previous_button.reply_text.split('<b>Ответ:</b>\n\n')[0] + \
            '<b>Ответ:</b>\n\n'+f"<code>{previous_button.any_data.get('answer')}</code>"
        return new_reply_text, self.next_state


class Utils(Base):

    list_children_buttons = [PostFeedback(), EditFeedback(),
                             GenerateNewResponseToFeedback(), DontReplyFeedback(), GoToBack(new=False)]
    message_to_edit_feedback = {FSMPersonalCabinetStates.edit_feedback_answer: MessageEditFeedbackAnswer()}

    async def send_request_for_phone_number(self, update, state):
        reply_text = 'Пожалуйста, введите номер телефона, указанный при регистрации в кабинете Wildberries. ' \
                     'Формат +7**********'
        next_state = FSMUtilsStates.message_after_user_enters_phone
        return reply_text, next_state

    async def send_request_for_sms_code(self, update, state, phone):
        phone = update.text.strip()
        if phone.startswith('+7') and phone.lstrip('+').isdigit() and len(phone) == 12:
            with self.dbase:
                if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                    wb_user.phone = phone
                    wb_user.save()
                    wb_user.sms_token = await self.wb_api.send_phone_number(phone, update)
                    wb_user.save()

            reply_text = 'Пожалуйста, введите код который пришёл в кабинет покупателя ' \
                         'Wildberries либо по смс на указанный номер телефона:'
            next_state = FSMUtilsStates.message_after_user_enters_sms_code
        else:
            reply_text = "Ошибка неправильный формат номера телефона, попробуйте ввести снова -> формат +7**********"
            next_state = None
        return reply_text, next_state

    async def get_access_to_wb_api(self, update, state,
                                         phone:  str | int | None = None,
                                         sms_code: str | int | None = None) -> tuple | str:
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                sellerToken = wb_user.sellerToken
                passportToken = wb_user.passportToken
                sms_token = wb_user.sms_token

        if not sellerToken and not passportToken and not phone and not sms_code:
            reply_text, next_state = await self.send_request_for_phone_number(update=update, state=state)
            return reply_text, next_state

        if phone:
            reply_text, next_state = await self.send_request_for_sms_code(update=update, state=state, phone=phone)
            return reply_text, next_state

        elif sms_code and sms_token:
            sellerToken = await self.wb_api.send_sms_code(sms_code=sms_code, sms_token=sms_token, update=update)
            if sellerToken:
                await self.wb_api.get_passport_token(seller_token=sellerToken, update=update)

        # if sellerToken:
        #     wb_user_id = await self.wb_api.introspect_seller_token(seller_token=sellerToken)
        #     if wb_user_id:
        #         passportToken = await self.wb_api.get_passport_token(seller_token=sellerToken, update=update)
        #
        #     else:
        #         sellerToken = await self.wb_api.get_seller_token_from_passport_token(passportToken)

        return sellerToken


    async def suppliers_buttons_logic(self, update, state):
        suppliers = []

        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                wb_user_suppliers = wb_user.suppliers
                seller_token = wb_user.sellerToken

            self.logger.debug(f'Utils: get suppliers buttons names from DB: {wb_user_suppliers}')

        if wb_user_suppliers:
            suppliers = await self.get_many_buttons_from_any_collections(get_buttons_list=wb_user_suppliers.keys())
            self.logger.debug(f'Utils: get suppliers buttons from collections: {suppliers}')

            if wb_user_suppliers and not suppliers:
                 suppliers = await self.utils_get_or_create_buttons(collection=wb_user_suppliers,
                                                                    class_type='supplier', update=update)
                 self.logger.debug(f'Utils: create suppliers buttons: {suppliers}')

        else:
            if seller_token:
                if suppliers := await self.wb_api.get_suppliers(seller_token=seller_token, update=update):
                    suppliers = await self.utils_get_or_create_buttons(suppliers, class_type='supplier', update=update)

            else:
                seller_token = await self.get_access_to_wb_api(update=update, state=state)
                if not isinstance(seller_token, tuple):
                    self.logger.debug(f'Utils: not suppliers recursive call suppliers_buttons_logic: {suppliers}')
                    suppliers = await self.suppliers_buttons_logic(update=update, state=state)

        return suppliers

    async def feedback_buttons_logic(self, supplier: dict | str, update) -> list:
        supplier_name_key = list(supplier.keys())[0] if isinstance(supplier, dict) else supplier
        feedbacks = None
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                feedbacks = wb_user.unanswered_feedbacks

        if feedbacks:
            """Выбираем неотвеченные отзывы конкретного supplier из БД"""
            feedbacks = {feedback_id: feedback_data for feedback_id, feedback_data in feedbacks.items()
                         if feedback_data.get('supplier') == supplier_name_key}
        else:
            """Если в БД нет отзывов делаем запрос к WB API"""
            msg = await self.bot.send_message(chat_id=update.from_user.id, text=self.default_download_information)
            feedbacks = await self.wb_api.get_feedback_list(
                seller_token=wb_user.sellerToken, supplier=supplier, update=update)
            await self.bot.delete_message(chat_id=update.from_user.id, message_id=msg.message_id)

        """Возвращаем список объектов BaseButton кнопок-отзывов"""
        return await self.utils_get_or_create_buttons(
            collection=feedbacks, class_type='feedback', update=update, supplier_name_key=supplier_name_key)

    async def create_button(self, data: dict, class_type: str, update, supplier_name_key: str | None = None):
        """Рекурсивное создание кнопок кабинетов и отзывов"""
        button = None
        reply_text = '<b>Выберите отзыв:</b>'

        for object_id, object_data in data.items():
            self.logger.debug(f'Utils: create_button: {object_id}, supplier: {supplier_name_key}')
            if object_id.startswith('Feedback'):
                dt, tm = object_data.get("createdDate")[:16].split("T")
                dt_tm = ' '.join(('-'.join(dt.split('-')[::-1]), tm))

                reply_text = '<b>Выберите отзыв:</b>' if class_type == 'Supplier' else \
                             f'<b>Товар:</b> {object_data.get("productName")}\n' \
                             f'<b>Дата:</b> {dt_tm}\n' \
                             f'<b>Оценка:</b> {object_data.get("productValuation")}\n' \
                             f'<b>Текст отзыва:</b> {object_data.get("text")}\n\n' \
                             f'<b>Ответ:</b>\n\n<code>{object_data.get("answer")}</code>'
                             # f'<b>Ответ:</b>\n\n' + self.default_generate_answer

            button = type(object_id, (BaseButton, ), {})(
                name=object_data.get('button_name'),
                parent_name='WildberriesCabinet' if class_type == 'Supplier' else supplier_name_key,
                reply_text=reply_text,
                any_data=object_data,
                messages=self.message_to_edit_feedback if class_type == 'Feedback' else None,
                next_state=FSMPersonalCabinetStates.edit_feedback_answer if class_type == 'Feedback' else None
            )

            children = self.list_children_buttons if class_type == 'Feedback' else \
                await self.feedback_buttons_logic(supplier=data, update=update)  # тут создаются новые кнопки отзывов

            button.children_buttons = children
            if isinstance(button.name, str) and class_type == 'Supplier':
                button.name += f' < {len(children)-1 if children else 0} >'

            button.reply_text = '📭 <b>Отзывов пока нет</b>' if len(children)-1 <= 0 else reply_text

        return button

    async def utils_get_or_create_buttons(self, collection: dict, class_type: str,
                                          update, supplier_name_key: str | None = None) -> list:
        class_type = class_type.title()
        if class_type not in ['Supplier', 'Feedback']:
            raise ValueError('class_type должен быть Supplier или Feedback')

        __buttons = list()

        for object_id, object_data in collection.items():
            """Проверяем существует ли объект-кнопка BaseButton В какой-либо коллекции"""
            button = await self.button_search_and_action_any_collections(action='get', button_name=object_id)

            if not button:
                """Если нет создаем новый объект"""
                button = await self.create_button(data={object_id: object_data},
                                                  class_type=class_type, update=update,
                                                  supplier_name_key=supplier_name_key)
            __buttons.append(button)

        __buttons.append(GoToBack(new=False))

        return __buttons


class UpdateListFeedbacks(BaseButton, Utils):

    def _set_name(self) -> str:
        return '🌐 Обновить информацию'

    def _set_reply_text(self) -> str | None:
        return '<b>Выберите отзыв:</b>'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        supplier_name_key = data.get('previous_button')
        feedbacks = None
        buttons = []

        msg = await self.bot.send_message(chat_id=update.from_user.id, text=self.default_download_information)

        with self.dbase:
            wb_user = self.tables.wildberries.get_or_none(user_id=update.from_user.id)

        if wb_user:
            feedbacks = await self.wb_api.get_feedback_list(
                seller_token=wb_user.sellerToken, supplier=supplier_name_key, update=update)
            await self.bot.delete_message(chat_id=update.from_user.id, message_id=msg.message_id)

        if feedbacks:
            buttons = await self.utils_get_or_create_buttons(
                collection=feedbacks, class_type='feedback', update=update, supplier_name_key=supplier_name_key)

        if not any(button.__class__.__name__.startswith('Feedback') for button in buttons):
            buttons = await self.feedback_buttons_logic(supplier=supplier_name_key, update=update)

        if supplier_name_key:
            supplier_button = await self.button_search_and_action_any_collections(action='get', button_name=supplier_name_key)
            supplier_button.children_buttons = buttons
            await self.change_name_button(supplier_button, len(buttons)-1)

        self.children_buttons = buttons
        # self.children_buttons.append(self)

        return self.reply_text, self.next_state


class MessageAfterUserEntersPhone(BaseMessage, Utils):
    def _set_state_or_key(self) -> str:
        return 'FSMUtilsStates:message_after_user_enters_phone'

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        reply_text, next_state = await self.get_access_to_wb_api(update=update, state=state, phone=update.text)
        return reply_text, next_state


class MessageAfterUserEntersSmsCode(BaseMessage, Utils):
    def _set_state_or_key(self) -> str:
        return 'FSMUtilsStates:message_after_user_enters_sms_code'

    def _set_next_state(self) -> str | None:
        return 'reset_state'

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        reply_text = "Код не верный, попробуйте немного позже"
        if await self.get_access_to_wb_api(update=update, state=state, sms_code=update.text):
            reply_text = "Код верный, получаю данные магазина ... "
        return reply_text, self.next_state


class WildberriesCabinet(BaseButton, Utils):

    def _set_name(self) -> str:
        return '🏪 Мои магазины'

    def _set_reply_text(self) -> str:
        return '<b>Выберите магазин:</b>'

    def _set_next_state(self) -> str | None:
        return 'reset_state'

    def _set_children(self) -> list:
        return [GoToBack(parent_id=self.button_id, parent_name=self.__class__.__name__)]
        # return [UpdateListFeedbacks(parent_id=self.button_id, parent_name=self.__class__.__name__),
        #         GoToBack(parent_id=self.button_id, parent_name=self.__class__.__name__)]

    def _set_messages(self) -> dict:
        messages = [MessageAfterUserEntersPhone(self.button_id, parent_name=self.__class__.__name__),
                    MessageAfterUserEntersSmsCode(self.button_id, parent_name=self.__class__.__name__)]
        return {message.state_or_key: message for message in messages}

    async def _set_answer_logic(self, update, state):
        reply_text, next_state = self.reply_text, self.next_state

        result = await self.get_access_to_wb_api(update=update, state=state)
        if isinstance(result, tuple):
            reply_text, next_state = result

        else:
            suppliers = await self.suppliers_buttons_logic(update=update, state=state)
            # suppliers.append(GoToBack(new=False))
            self.children_buttons = suppliers

        return reply_text, next_state


class AroundTheClock(BaseButton):
    def _set_name(self) -> str:
        return 'Круглосуточно'

    def _set_reply_text(self) -> str:
        return 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                wb_user.notification_times = 'around_the_clock'
                wb_user.save()
        return self.reply_text, self.next_state


class DayFrom9To18Hours(BaseButton):
    def _set_name(self) -> str:
        return 'День с 9 до 18 часов'

    def _set_reply_text(self) -> str:
        return 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                wb_user.notification_times = '9-18'
                wb_user.save()
        return self.reply_text, self.next_state


class FullDayFrom9To21Hours(BaseButton):
    def _set_name(self) -> str:
        return 'Полный день с 9 до 21 часа'

    def _set_reply_text(self) -> str:
        return 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                wb_user.notification_times = '9-21'
                wb_user.save()
        return self.reply_text, self.next_state


class MessageEnterYourselfSetUpNotificationTimes(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:enter_yourself_set_up_notification_times'

    def _set_reply_text(self) -> str:
        return 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        enter_data = update.text.replace(' ', '')
        period = enter_data.split('-')
        if len(period) == 2 \
                and all([sym.isdigit() and int(sym) in range(25) for sym in period]) and period[0] > period[1]:
            self.children_buttons = self._set_children()
            with self.dbase:
                if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                    wb_user.notification_times = enter_data
                    wb_user.save()
            # TODO логика настройки уведомлений wildberries
            text = self.reply_text
            next_state = 'reset_state'
        else:
            text = self.default_incorrect_data_input_text
            self.children_buttons.clear()
            next_state = None
        return text, next_state


class EnterYourself(BaseButton):
    def _set_name(self) -> str:
        return 'Ввести самостоятельно'

    def _set_reply_text(self) -> str:
        return 'Введите период времени в формате: 9 - 18'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_next_state(self) -> str | None:
        return FSMPersonalCabinetStates.enter_yourself_set_up_notification_times

    def _set_messages(self) -> dict:
        message = MessageEnterYourselfSetUpNotificationTimes(self.button_id)
        return {message.state_or_key: message}


class SetUpNotificationTimes(BaseButton):
    def _set_name(self) -> str:
        return '"⏰ Время получения уведомлений'

    def _set_reply_text(self) -> str:
        return '<b>Выберите удобное время уведомления:</b>'

    def _set_children(self) -> list:
        return [AroundTheClock(parent_name=self.__class__.__name__),
                DayFrom9To18Hours(parent_name=self.__class__.__name__),
                FullDayFrom9To21Hours(parent_name=self.__class__.__name__),
                EnterYourself(parent_name=self.__class__.__name__),
                # GoToBack(new=False)
                ]


class MessageEnterSignatureForSignatureToTheAnswerButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:enter_signature'

    def _set_reply_text(self) -> str:
        return 'Ваша новая подпись сохранена'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        reply_text, next_state = self.reply_text, self.next_state
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                wb_user.signature_to_answer = update.text
                wb_user.save()
        #TODO логика записи подписи в wildberries

        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message_id)
        data = await state.get_data()
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=data.get('last_handler_sent_message_id'))
        button = await self.button_search_and_action_any_collections(action='get', button_name=self.parent_name)
        if button:
            reply_text, next_state = await button._set_answer_logic(update, state)
        return reply_text, next_state


class SignatureToTheAnswer(BaseButton, Utils):
    def _set_name(self) -> str:
        return '✒ Управление подписями к ответу'

    def _set_reply_text(self) -> str:
        return '<b>Введите новую подпись пожалуйста:</b>'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.enter_signature

    def _set_messages(self) -> dict:
        messages = [
            MessageEnterSignatureForSignatureToTheAnswerButton(self.button_id, parent_name=self.__class__.__name__)]
        return {message.state_or_key: message for message in messages}

    async def _set_answer_logic(self, update, state: FSMContext):
        signature = self.default_bad_text
        with self.dbase:
            if wb_user := self.tables.wildberries.get_or_none(user_id=update.from_user.id):
                signature = wb_user.signature_to_answer

        reply_text, next_state = f"<b>Ваша подпись:</b>\n{signature}\n\n" + self.reply_text, self.next_state

        result = await self.get_access_to_wb_api(update=update, state=state)
        if isinstance(result, tuple):
            reply_text, next_state = result

        return reply_text, next_state

create_buttons = [UpdateListFeedbacks()]

