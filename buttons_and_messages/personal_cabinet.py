import re

from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from buttons_and_messages.time_zones import MoscowUtcUp3, KaliningradUtcUp2, SamaraUtcUp4, EkaterinburgAndAktauUtcUp5, \
    OmskAndNurSultanUtcUp6, KrasnoyarskUtcUp7, IrkutskUtcUp8, YakutskUtcUp9, VladivostokUtcUp10, MagadanUtcUp11, \
    KamchatkaUtcUp12
from config import BOT_NIKNAME
from utils.states import FSMPersonalCabinetStates
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
        return '📨 Опубликовать'


class EditFeedback(BaseButton):
    def _set_name(self) -> str:
        return '✏ Редактировать'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)

        data = await state.get_data()
        previous_button = self.feedback_collection.get(data.get('previous_button'))
        reply_text = previous_button.any_data.get('answer')
        self.reply_text = reply_text

        return self.reply_text, self.next_state


class GenerateNewResponseToFeedback(BaseButton):
    def _set_name(self) -> str:
        return '🔄 Сгенерировать новый ответ'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message.message_id)
        message_waiting = await self.bot.send_message(chat_id=update.from_user.id, text=self.default_generate_answer)

        data = await state.get_data()
        previous_button = self.feedback_collection.get(data.get('previous_button'))
        reply_feedback = await self.ai.reply_feedback(previous_button.any_data.get('text'))
        previous_button.any_data['answer'] = reply_feedback
        self.children_buttons = previous_button.children_buttons

        await self.bot.delete_message(chat_id=update.from_user.id, message_id=message_waiting.message_id)

        return previous_button.reply_text + f"<code>{previous_button.any_data.get('answer')}</code>", self.next_state


class DontReplyFeedback(BaseButton):
    def _set_name(self) -> str:
        return '⛔ Не отвечать на отзыв'

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        data = await state.get_data()
        removed_button = self.feedback_collection.pop(data.get('previous_button'))
        supplier_button = self.supplier_collection.get(removed_button.parent_name)
        supplier_button.children_buttons.remove(removed_button)
        self.children_buttons = supplier_button.children_buttons

        was = re.search(r'< \d+ >', supplier_button.name).group(0)
        will_be = f"< {int(was.strip('<> ')) - 1} >"
        supplier_button.name = supplier_button.name.replace(was, will_be)

        return supplier_button.reply_text, supplier_button.next_state


class MessageEditFeedbackAnswer(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:edit_feedback_answer'

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        data = await state.get_data()
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=update.message_id)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=data.get('last_handler_sent_message_id'))
        previous_button = self.feedback_collection.get(data.get('previous_button'))
        previous_button.any_data['answer'] = update.text.replace(f'@{BOT_NIKNAME}', '').strip().strip('\n').strip()
        self.children_buttons = previous_button.children_buttons

        return previous_button.reply_text + f"<code>{previous_button.any_data.get('answer')}</code>", self.next_state


class Utils(Base):

    list_children_buttons = [PostFeedback(), EditFeedback(),
                             GenerateNewResponseToFeedback(), DontReplyFeedback(), GoToBack(new=False)]
    message_to_edit_feedback = {FSMPersonalCabinetStates.edit_feedback_answer: MessageEditFeedbackAnswer()}

    async def feedback_buttons_logic(self, supplier: dict, update):
        # print('supplier_button =', f'Supplier{list(supplier.keys())[0]}')
        # print('supplier_button =', self.supplier_collection.get(f'Supplier{list(supplier.keys())[0]}'))
        __buttons = list()
        with self.dbase:
            wb_user = self.tables.wildberries.get_or_none(user_id=update.from_user.id)

        if feedbacks := wb_user.unanswered_feedbacks:
            __buttons = await self.utils_get_or_create_buttons(feedbacks, class_type='feedback', update=update)

        elif feedbacks := await self.wb_api.get_feedback_list(seller_token=wb_user.sellerToken, supplier=supplier):
            result = dict()
            for feedback_id, feedback_data in feedbacks.items():
                result.update({feedback_id: {'name': f"[ {feedback_data.get('productValuation')} ]  "
                                                     f"{feedback_data.get('text')[:45]}", **feedback_data}})

            __buttons = await self.utils_get_or_create_buttons(result, class_type='feedback', update=update,
                                                               supplier=f'Supplier{list(supplier.keys())[0]}')

        return __buttons

    async def create_button(self, data: dict, class_type: str, update, supplier: str | None = None):
        """Рекурсивное создание кнопок кабинетов и отзывов"""
        # print('supplier_button =', supplier)
        # print('supplier_button =', self.supplier_collection.get(supplier))

        button = None
        # children = self.list_children_buttons if class_type == 'Feedback' else \
        #                 await self.feedback_buttons_logic(supplier=data, update=update)

        for object_id, object_data in data.items():
            reply_text = '<b>Выберите отзыв:</b>' if class_type == 'Supplier' else \
                         f'<b>Товар:</b> {object_data.get("productName")}\n' \
                         f'<b>Дата:</b> {object_data.get("createdDate")[:16].replace("T", " ")}\n' \
                         f'<b>Оценка:</b> {object_data.get("productValuation")}\n' \
                         f'<b>Текст отзыва:</b> {object_data.get("text")}\n\n' \
                         f'<b>Ответ:</b>\n\n' + self.default_generate_answer

            # print('create_button answer:', object_data.get('answer'))
            # object_data['answer'] = self.default_generate_answer

            button = type(f'{class_type}{object_id}', (BaseButton, ), {})(
                name=object_data.get("name"),
                parent_name='WildberriesCabinet' if class_type == 'Supplier' else supplier,
                reply_text=reply_text,
                any_data=object_data,
                messages=self.message_to_edit_feedback if class_type == 'Feedback' else None,
                next_state=FSMPersonalCabinetStates.edit_feedback_answer if class_type == 'Feedback' else None
            )
            children = self.list_children_buttons if class_type == 'Feedback' else \
                await self.feedback_buttons_logic(supplier=data, update=update)

            button.children_buttons = children
            if isinstance(button.name, str) and class_type == 'Supplier':
                button.name += f' < {len(children)-1 if children else 0} >'
        # print('supplier_collection:', self.supplier_collection)

        return button

    async def utils_get_or_create_buttons(self, collection: dict, class_type: str, update, supplier: str | None = None) -> list:
        class_type = class_type.title()
        if class_type not in ['Supplier', 'Feedback']:
            raise ValueError('class_type должен быть Supplier или Feedback')

        __buttons = list()
        for object_id, object_data in collection.items():
            button = self.supplier_collection.get(f'{class_type}{object_id}') if class_type == 'Supplier' else \
                self.feedback_collection.get(f'{class_type}{object_id}')
            if not button:
                button = await self.create_button(data={object_id: object_data}, class_type=class_type, update=update,
                                                  supplier=supplier)
            __buttons.append(button)

        __buttons.append(GoToBack(new=False))
        return __buttons


class MessageFirstWildberriesCabinet(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:enter_in_wildberries_cabinet'

    def _set_children(self) -> list:
        return [GoToBack(parent_id=self.button_id)]

    async def _set_answer_logic(self, update, state: FSMContext):
        phone = update.text.strip()
        if phone.startswith('+7') and phone.lstrip('+').isdigit() and len(phone) == 12:

            await self.wb_api.send_phone_number(phone, update)
            reply_text = 'Пожалуйста, введите код который пришёл в кабинет покупателя ' \
                         'Wildberries либо по смс на указанный номер телефона.'
            next_state = FSMPersonalCabinetStates.wildberries_cabinet_enter_code_from_sms
        else:
            reply_text = self.default_incorrect_data_input_text
            next_state = None
        return reply_text, next_state


class MessageEnterCodeFromSmsForWildberriesCabinet(BaseMessage, Utils):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:wildberries_cabinet_enter_code_from_sms'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        next_state = 'reset_state'
        reply_text = self.default_incorrect_data_input_text

        with self.dbase:
            wb_user = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
            sms_token = wb_user.sms_token

        if seller_token := await self.wb_api.send_sms_code(sms_code=update.text, sms_token=sms_token, update=update):
            await self.wb_api.get_passport_token(seller_token=seller_token, update=update)
            if suppliers := await self.wb_api.get_suppliers(seller_token=seller_token, update=update):
                self.children_buttons = await self.utils_get_or_create_buttons(suppliers, class_type='supplier', update=update)
                reply_text = 'Выберите магазин:'

        return reply_text, next_state


class WildberriesCabinet(BaseButton, Utils):

    def _set_name(self) -> str:
        return '🏪 Мои магазины'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.enter_in_wildberries_cabinet

    def _set_reply_text(self) -> str:
        return 'Пожалуйста, введите номер телефона, указанный при регистрации в кабинете Wildberries. ' \
               'Формат +7**********'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_messages(self) -> dict:
        messages = [MessageFirstWildberriesCabinet(self.button_id, parent_name=self.__class__.__name__),
                    MessageEnterCodeFromSmsForWildberriesCabinet(self.button_id, parent_name=self.__class__.__name__)]
        return {message.state_or_key: message for message in messages}

    async def _set_answer_logic(self, update, state):
        reply_text, next_state = 'Выберите магазин:', None
        with self.dbase:
            wb_user = self.tables.wildberries.get_or_none(user_id=update.from_user.id)

        if suppliers := wb_user.suppliers:
            self.children_buttons = await self.utils_get_or_create_buttons(suppliers, class_type='supplier', update=update)

        elif seller_token := wb_user.sellerToken:
            wb_user_id = await self.wb_api.introspect_seller_token(seller_token)
            if not wb_user_id:
                if passport_token := wb_user.passportToken:
                    seller_token = await self.wb_api.get_seller_token_from_passport_token(passport_token)

            if suppliers := await self.wb_api.get_suppliers(seller_token=seller_token, update=update):
                self.children_buttons = await self.utils_get_or_create_buttons(suppliers, class_type='supplier', update=update)
        else:
            reply_text, next_state = self.reply_text, self.next_state

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
            wb_row = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
            wb_row.notification_times = 'around_the_clock'
            wb_row.save()
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
            wb_row = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
            wb_row.notification_times = '9-18'
            wb_row.save()
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
            wb_row = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
            wb_row.notification_times = '9-21'
            wb_row.save()
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
            print(self.children_buttons)
            with self.dbase:
                wb_row = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
                wb_row.notification_times = enter_data
                wb_row.save()
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
                GoToBack(new=False)]


class MessageFirstForSignatureToTheAnswerButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:signature_to_the_answer'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        phone = update.text.strip()
        if phone.startswith('+7') and phone.lstrip('+').isdigit() and len(phone) == 12:
            with self.dbase:
                wb_row = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
                wb_row.phone = phone
                wb_row.save()
            # TODO логика отправки сообщения wildberries
            text = 'Пожалуйста, введите код который пришёл в кабинет покупателя ' \
                   'Wildberries либо по смс на указанный номер телефона.'
            next_state = FSMPersonalCabinetStates.signature_to_the_answer_enter_code_from_sms
        else:
            text = self.default_incorrect_data_input_text
            next_state = None
        return text, next_state


class MessageEnterCodeFromSmsForSignatureToTheAnswerButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:signature_to_the_answer_enter_code_from_sms'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        next_state = None
        text = 'Ошибка, попробуйте еще раз'

        if update.text == '777':  # TODO логика проверки кода wildberries
            next_state = FSMPersonalCabinetStates.enter_signature
            text = 'Код верный -> введите новую подпись'

        return text, next_state


class MessageEnterSignatureForSignatureToTheAnswerButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:enter_signature'

    def _set_reply_text(self) -> str:
        return 'Ваша подпись сохранена в БД -> логика работы с WB в разработке'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        #TODO логика записи подписи в wildberries
        with self.dbase:
            wb_row = self.tables.wildberries.get_or_none(user_id=update.from_user.id)
            wb_row.signature_to_answer = update.text
            wb_row.save()
        return self.reply_text, self.next_state


class SignatureToTheAnswer(BaseButton):
    def _set_name(self) -> str:
        return '✒ Управление подписями к ответу'

    def _set_reply_text(self) -> str:
        return 'Пожалуйста, введите номер телефона, указанный при регистрации в кабинете Wildberries. ' \
               'Формат +7**********'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.signature_to_the_answer

    def _set_messages(self) -> dict:
        messages = [MessageFirstForSignatureToTheAnswerButton(self.button_id, parent_name=self.__class__.__name__),
                    MessageEnterCodeFromSmsForSignatureToTheAnswerButton(self.button_id, parent_name=self.__class__.__name__),
                    MessageEnterSignatureForSignatureToTheAnswerButton(self.button_id, parent_name=self.__class__.__name__)]
        return {message.state_or_key: message for message in messages}
