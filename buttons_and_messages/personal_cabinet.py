import asyncio

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


class UpdateListFeedbacks(BaseButton, Utils):

    def _set_name(self) -> str:
        return '🌐 Обновить информацию'

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Выберите отзыв:</b>'

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext) -> tuple[str, str | None]:
        reply_text, next_state = self.reply_text, self.next_state
        data = await state.get_data()
        user_id = update.from_user.id
        supplier_name_key = data.get('previous_button')
        supplier_button = None
        feedbacks = dict()
        buttons = []

        """Берем имя магазина из своей коллекции"""
        supplier_name_key = await self.button_search_and_action_any_collections(user_id=user_id, action='get',
                                                                                button_name='previous_button',
                                                                                updates_data=True)
        if supplier_name_key:
            supplier_button = await self.button_search_and_action_any_collections(
                user_id=user_id, action='get', button_name=supplier_name_key)

        if not supplier_button:
            return self.default_not_feeds_in_supplier, self.next_state

        supplier_button = await self.update_button_children_buttons_from_db(user_id=user_id,
                                                                            supplier_button=supplier_button)
        if len(supplier_button.children_buttons) > NUM_FEED_BUTTONS:
            self.children_buttons = supplier_button.children_buttons

        else:
            msg = await self.bot.send_message(chat_id=user_id, text=self.default_download_information.format(
                about='Загружаю информацию'))
            if supplier_name_key.startswith('SupplierParsing'):
                await self.wb_parsing(supplier_id=supplier_name_key, update=update)
            else:
                await self.wb_api.get_feedback_list(supplier=supplier_name_key, user_id=user_id)

            wb_user = self.dbase.wb_user_get_or_none(user_id=user_id)

            await self.bot.delete_message(chat_id=user_id, message_id=msg.message_id)

            feedbacks = dict(list({key: val for key, val in wb_user.unanswered_feedbacks.items()
                                   if key == supplier_name_key})[0:NUM_FEED_BUTTONS])

            buttons = await self.utils_get_or_create_buttons(collection=feedbacks, class_type='feedback', update=update,
                                                             supplier_name_key=supplier_name_key, user_id=user_id)
            if not any(button.class_name.startswith('Feedback') for button in buttons):
                buttons = await self.feedback_buttons_logic(supplier=supplier_name_key, update=update)

            # if supplier_name_key:
            #     supplier_button = await self.button_search_and_action_any_collections(
            #         user_id=user_id, action='get', button_name=supplier_name_key)

            supplier_button.children_buttons = buttons

            unfeeds_supplier = [feed for feed in wb_user.unanswered_feedbacks.values()
                                if feed.get('supplier') == supplier_button.class_name]

            await self.m_utils.change_name_button(button=supplier_button, num=len(unfeeds_supplier))

            self.children_buttons = buttons

            if not [button for button in self.children_buttons if button.class_name != 'GoToBack']:
                reply_text = self.default_not_feeds_in_supplier

        return reply_text, next_state


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
        reply_text, next_state = f'{FACE_BOT} Код не верный, попробуйте немного позже', self.next_state
        user_id = update.from_user.id

        if await self.get_access_to_wb_api(update=update, state=state, sms_code=update.text):
            reply_text, next_state = self.parent_button.reply_text, self.next_state
            if suppliers_buttons := await self.api_suppliers_buttons_logic(update=update, state=state, user_id=user_id):
                self.children_buttons = suppliers_buttons

        return reply_text, next_state


class SelectAPIMode(BaseButton, Utils):
    def _set_name(self) -> str:
        return 'Магазины по API \t 🔐'  # 🔑 🔐 🗝

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Выберите магазин:</b>'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_messages(self) -> dict:
        messages = [MessageAfterUserEntersPhone(button=self, parent_name=self.class_name, parent_button=self),
                    MessageAfterUserEntersSmsCode(button=self, parent_name=self.class_name, parent_button=self)]
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

                back_button = GoToBack(new=False)
                if not back_button in self.children_buttons:
                    self.children_buttons.append(back_button)

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
        user_id = update.from_user.id
        supplier_id = await self.m_utils.check_data(update.text)
        if supplier_id:
            # wait_msg = await self.bot.send_message(
            #     chat_id=update.from_user.id,
            #     text=self.default_download_information.format(about='Загружаю информацию о магазине')
            # )

            wb_user = self.dbase.wb_user_get_or_none(user_id=user_id)
            if supplier_id in [str(val.get('oldID')) for key, val in wb_user.suppliers.items()]:
                self.children_buttons = []
                return FACE_BOT + f'<b>Этот магазин уже в списке ваших магазинов</b>', None

            reply_text, next_state = self.default_service_in_dev, self.next_state

            await self.wb_parsing(supplier_id=supplier_id, update=update, user_id=user_id)

            if suppliers_buttons := await self.parsing_suppliers_buttons_logic(
                    update=update, state=state, user_id=user_id):

                reply_text = self.reply_text
                self.children_buttons = suppliers_buttons

            else:
                reply_text, next_state = f'Магазин с ID: {supplier_id} не найден, проверьте ID', None

            # await self.bot.delete_message(chat_id=update.from_user.id, message_id=wait_msg.message_id)
        else:
            reply_text, next_state = self.default_incorrect_data_input_text.format(text='введите ID магазина'), None
            self.children_buttons = []

        return reply_text, next_state


class EnterSupplierID(BaseButton):
    def _set_name(self) -> str:
        return '🔍 \t 📥 \t Добавить магазин'  # 🔍 🔎 📥

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Введите ID вашего магазина:</b>'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_next_state(self) -> str | None:
        return FSMUtilsStates.enter_supplier_id_mode

    def _set_messages(self) -> dict:
        message = MessageEnterSupplierIDMode(button=self)
        return {message.state_or_key: message}


class SelectSupplierIDMode(BaseButton, Utils):
    def _set_name(self) -> str:
        return 'Магазины по ID \t 🆓'  # 📖 🆓 🔓

    def _set_reply_text(self) -> str | None:
        return FACE_BOT + '<b>Выберите магазин:</b>'

    def _set_children(self) -> list:
        return [EnterSupplierID(parent_name=self.class_name, parent_button=self), GoToBack(new=False)]

    async def _set_answer_logic(self, update, state):
        reply_text, next_state = FACE_BOT + ' <b>Магазинов пока нет, добавьте</b>', self.next_state

        if parsing_suppliers := await self.parsing_suppliers_buttons_logic(update=update, state=state,
                                                                           user_id=update.from_user.id):
            reply_text = self.reply_text

            back = GoToBack(new=False)
            enter_supplier = EnterSupplierID(new=False)
            if back in parsing_suppliers:
                index_back = parsing_suppliers.index(back)
                parsing_suppliers.insert(index_back, enter_supplier)
            else:
                parsing_suppliers = parsing_suppliers + [enter_supplier, back]

            self.children_buttons = parsing_suppliers
        return reply_text, next_state


class WildberriesCabinet(BaseButton):

    def _set_name(self) -> str:
        return '🏪 \t Мои магазины'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите список магазинов:</b>'

    def _set_next_state(self) -> str | None:
        return 'reset_state'

    def _set_children(self) -> list:
        return [SelectAPIMode(parent_name=self.class_name, parent_button=self),
                SelectSupplierIDMode(parent_name=self.class_name, parent_button=self),
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
        return '⏰ \t Время получения уведомлений'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите удобное время уведомления:</b>'

    def _set_children(self) -> list:
        return [AroundTheClock(parent_name=self.class_name, parent_button=self),
                DayFrom9To18Hours(parent_name=self.class_name, parent_button=self),
                FullDayFrom9To21Hours(parent_name=self.class_name, parent_button=self),
                EnterYourself(parent_name=self.class_name, parent_button=self),
                GoToBack(new=False)
                ]


class MessageEnterSignatureForSignatureToTheAnswerButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMPersonalCabinetStates:enter_signature'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    async def _set_answer_logic(self, update, state: FSMContext):
        user_id = update.from_user.id
        reply_text, next_state = self.default_bad_text, self.next_state

        if update.text.replace('"', '').replace(' ', '') == 'del':
            new_signature = None
            wait_msg_text = '<b>Подпись удалена</b>'
        else:
            new_signature = update.text
            wait_msg_text = '<b>Новая подпись установлена</b>'

        self.dbase.update_wb_user(
            user_id=user_id,
            update_data={'signature_to_answer': new_signature}
        )

        await self.bot.delete_message(chat_id=user_id, message_id=update.message_id)

        data = await state.get_data()
        await self.bot.delete_message(chat_id=user_id, message_id=data.get('last_handler_sent_message_id'))

        wait_msg = await self.bot.send_message(
            chat_id=user_id, text=FACE_BOT + wait_msg_text)
        await asyncio.sleep(1)
        await self.bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)

        button = await self.button_search_and_action_any_collections(user_id=user_id, action='get',
                                                                     button_name=self.parent_name)
        if button:
            reply_text, next_state = await button._set_answer_logic(update, state)
        return reply_text, next_state


class SignatureToTheAnswer(BaseButton, Utils):
    def _set_name(self) -> str:
        return '🪶 \t Управление подписями к ответу'  # 🪶 ✒ 🖋 📝

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Введите новую подпись{var}:</b>'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.enter_signature

    def _set_children(self) -> list:
        return [GoToBack(new=False)]

    def _set_messages(self) -> dict:
        messages = [MessageEnterSignatureForSignatureToTheAnswerButton(self.button_id, parent_name=self.class_name)]
        return {message.state_or_key: message for message in messages}

    async def _set_answer_logic(self, update, state: FSMContext):
        signature = None

        if wb_user := self.dbase.wb_user_get_or_none(user_id=update.from_user.id):
            signature = wb_user.signature_to_answer

        if signature:
            reply_text, next_state = f"<b>Ваша подпись:</b>\n\n{signature}\n\n" + \
                                     self.reply_text.format(var='или "del" для удаления'), self.next_state
        else:
            reply_text, next_state = f"<b>Подпись не установлена</b>\n\n" + \
                                     self.reply_text.format(var=''), self.next_state

        return reply_text, next_state


create_buttons = [UpdateListFeedbacks()]
