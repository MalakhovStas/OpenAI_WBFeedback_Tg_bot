import itertools

from aiogram.dispatcher import FSMContext
from aiogram.types import CallbackQuery, Message

from buttons_and_messages.time_zones import MoscowUtcUp3, KaliningradUtcUp2, SamaraUtcUp4, EkaterinburgAndAktauUtcUp5, \
    OmskAndNurSultanUtcUp6, KrasnoyarskUtcUp7, IrkutskUtcUp8, YakutskUtcUp9, VladivostokUtcUp10, MagadanUtcUp11, \
    KamchatkaUtcUp12
from config import NUM_FEED_BUTTONS, FACE_BOT
from utils.states import FSMPersonalCabinetStates, FSMUtilsStates
from .base_classes import Utils, BaseButton, BaseMessage, GoToBack

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


# Au7n8BPw0O7ADPCM2MEMQh1PfoKMeTuH7CT-Pnn-_eIHretpsewN14c9_5RyptC0DYc7ttIvfxBTYkcDfzyhNoe2Vq_haFr4MksJ8LKogBwrtA


class UpdateListFeedbacks(BaseButton, Utils):

    def _set_name(self) -> str:
        return '🌐 Обновить информацию'

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Выберите отзыв:</b>'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext) -> tuple[str, str | None]:
        data = await state.get_data()
        user_id = update.from_user.id
        supplier_name_key = data.get('previous_button')

        # todo убрать
        # print('supplier_name_key', supplier_name_key)

        feedbacks = dict()
        buttons = []

        msg = await self.bot.send_message(chat_id=user_id, text=self.default_download_information)

        await self.wb_api.get_feedback_list(supplier=supplier_name_key, user_id=user_id)

        wb_user = self.dbase.wb_user_get_or_none(user_id=user_id)

        await self.bot.delete_message(chat_id=user_id, message_id=msg.message_id)

        if feedbacks := dict(itertools.islice(wb_user.unanswered_feedbacks.items(), NUM_FEED_BUTTONS)):
            buttons = await self.utils_get_or_create_buttons(
                collection=feedbacks, class_type='feedback', update=update,
                supplier_name_key=supplier_name_key, user_id=user_id)

            if not any(button.class_name.startswith('Feedback') for button in buttons):
                buttons = await self.feedback_buttons_logic(supplier=supplier_name_key, update=update)

        if supplier_name_key:
            supplier_button = await self.button_search_and_action_any_collections(action='get',
                                                                                  button_name=supplier_name_key)
            supplier_button.children_buttons = buttons
            # await self.change_name_button(supplier_button, len(buttons) - 1)
            unfeeds_supplier = [feed for feed in wb_user.unanswered_feedbacks.values()
                                if feed.get('supplier') == supplier_button.__class__.__name__]
            await self.m_utils.change_name_button(supplier_button, len(unfeeds_supplier))

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


class SelectAPIMode(BaseButton, Utils):
    def _set_name(self) -> str:
        return 'Режим работы по API'

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Выберите магазин:</b>'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_messages(self) -> dict:
        messages = [MessageAfterUserEntersPhone(button=self, parent_name=self.class_name),
                    MessageAfterUserEntersSmsCode(button=self, parent_name=self.class_name)]
        return {message.state_or_key: message for message in messages}

    async def _set_answer_logic(self, update: Message, state: FSMContext):
        reply_text, next_state = self.reply_text, self.next_state
        user_id = update.from_user.id

        result = await self.get_access_to_wb_api(update=update, state=state)
        if isinstance(result, tuple):
            reply_text, next_state = result
        else:
            if suppliers_buttons := await self.api_suppliers_buttons_logic(update=update, state=state, user_id=user_id):
                self.children_buttons = suppliers_buttons

        return reply_text, next_state


class MessageEnterSupplierIDMode(BaseMessage, Utils):
    def _set_state_or_key(self) -> str:
        return 'FSMUtilsStates:enter_supplier_id_mode'

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Магазин добавлен успешно</b>'

    def _set_next_state(self) -> str | None:
        return 'reset_state'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update: Message, state: FSMContext | None = None):
        supplier_id = await self.m_utils.check_data(update.text)

        if supplier_id:
            reply_text, next_state = self.default_service_in_dev, self.next_state  # тут нужно reset state
            supplier = await self.wb_parsing(supplier_id=supplier_id, update=update)

            # TODO вызываем менеджера по парсингу для поиска и создания нового supplier и его feedbacks
            if suppliers_buttons := await self.parsing_suppliers_buttons_logic(
                    update=update, state=state, user_id=update.from_user.id):

                reply_text = self.reply_text
                self.children_buttons = suppliers_buttons

            else:
                reply_text, next_state = f'Магазин с ID: {supplier_id} не найден, проверьте ID', None
        else:
            reply_text, next_state = self.default_incorrect_data_input_text.format(text='введите ID магазина'), None

        return reply_text, next_state


class EnterSupplierID(BaseButton):
    def _set_name(self) -> str:
        return 'Добавить магазин'

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + 'Введите ID вашего магазина'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_next_state(self) -> str | None:
        return FSMUtilsStates.enter_supplier_id_mode

    def _set_messages(self) -> dict:
        message = MessageEnterSupplierIDMode(button=self)
        return {message.state_or_key: message}


class SelectSupplierIDMode(BaseButton, Utils):
    def _set_name(self) -> str:
        return 'Работа по ID магазина'

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Выберите магазин:</b>'

    def _set_children(self) -> list:
        return [EnterSupplierID(parent_button=self, parent_name=self.class_name), GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        reply_text, next_state = FACE_BOT + ' <b>Магазинов пока нет, добавьте</b>', self.next_state

        if parsing_suppliers := await self.parsing_suppliers_buttons_logic(update=update, state=state,
                                                                           user_id=update.from_user.id):
            reply_text = self.reply_text
            self.children_buttons = parsing_suppliers

        return reply_text, next_state


class WildberriesCabinet(BaseButton):

    def _set_name(self) -> str:
        return '🏪 Мои магазины'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Выберите режим работы:'

    def _set_next_state(self) -> str | None:
        return 'reset_state'

    def _set_children(self) -> list:
        return [SelectAPIMode(parent_button=self, parent_name=self.class_name),
                SelectSupplierIDMode(parent_button=self, parent_name=self.class_name),
                GoToBack(new=False)]


class AroundTheClock(BaseButton):
    def _set_name(self) -> str:
        return 'Круглосуточно'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'notification_times': 'around_the_clock'}
        )

        return self.reply_text, self.next_state


class DayFrom9To18Hours(BaseButton):
    def _set_name(self) -> str:
        return 'День с 9 до 18 часов'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'notification_times': '9-18'}
        )
        return self.reply_text, self.next_state


class FullDayFrom9To21Hours(BaseButton):
    def _set_name(self) -> str:
        return 'Полный день с 9 до 21 часа'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'notification_times': '9-21'}
        )
        return self.reply_text, self.next_state


class MessageEnterYourselfSetUpNotificationTimes(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:enter_yourself_set_up_notification_times'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Укажите ваш часовой пояс, чтобы я мог правильно отслеживать время 🕐'

    def _set_children(self) -> list:
        return timezones + [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        enter_data = update.text.replace(' ', '')
        period = enter_data.split('-')
        if len(period) == 2 and all([sym.isdigit() and int(sym) in range(25) for sym in period]):
            # and period[0] > period[1]:

            self.children_buttons = self._set_children()
            self.dbase.update_wb_user(
                user_id=update.from_user.id,
                update_data={'notification_times': enter_data}
            )

            text = self.reply_text
            next_state = 'reset_state'
        else:
            text = self.default_incorrect_data_input_text.format(text='необходимо ввести период времени в формате 5-17')
            self.children_buttons.clear()
            next_state = None
        return text, next_state


class EnterYourself(BaseButton):
    def _set_name(self) -> str:
        return 'Ввести самостоятельно'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Введите период времени в формате: 9 - 18'

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
        return FACE_BOT + '<b>Выберите удобное время уведомления:</b>'

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
        return FACE_BOT + 'Ваша новая подпись сохранена'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        reply_text, next_state = self.reply_text, self.next_state

        self.dbase.update_wb_user(
            user_id=update.from_user.id,
            update_data={'signature_to_answer': update.text}
        )

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
        return FACE_BOT + '<b>Введите новую подпись пожалуйста:</b>'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.enter_signature

    def _set_messages(self) -> dict:
        messages = [
            MessageEnterSignatureForSignatureToTheAnswerButton(self.button_id, parent_name=self.__class__.__name__)]
        return {message.state_or_key: message for message in messages}

    async def _set_answer_logic(self, update, state: FSMContext):
        signature = self.default_bad_text

        if wb_user := self.dbase.wb_user_get_or_none(user_id=update.from_user.id):
            signature = wb_user.signature_to_answer

        reply_text, next_state = f"<b>Ваша подпись:</b>\n\n{signature}\n\n" + self.reply_text, self.next_state
        # result = await self.get_access_to_wb_api(update=update, state=state)
        # if isinstance(result, tuple):
        #     reply_text, next_state = result

        return reply_text, next_state


create_buttons = [UpdateListFeedbacks()]
