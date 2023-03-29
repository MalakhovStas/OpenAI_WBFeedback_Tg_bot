from buttons_and_messages.personal_cabinet import WildberriesCabinet, SetUpNotificationTimes, SignatureToTheAnswer
from config import SUPPORT, FACE_BOT, NUM_FEED_BUTTONS
from utils.states import FSMMainMenuStates, FSMPersonalCabinetStates
from .base_classes import BaseButton, BaseMessage, Utils
from aiogram.types import CallbackQuery
from aiogram.dispatcher import FSMContext


class PersonalCabinet(BaseButton):

    def _set_name(self) -> str:
        return '⚙ \t Личный кабинет'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите пункт меню:</b>'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.personal_cabinet

    def _set_children(self) -> list:
        return [WildberriesCabinet(parent_name=self.class_name, parent_button=self),
                SetUpNotificationTimes(parent_name=self.class_name, parent_button=self),
                SignatureToTheAnswer(parent_name=self.class_name, parent_button=self)]


class AnswerManagement(BaseButton, Utils):
    wb_cabinet = WildberriesCabinet(new=False)

    def _set_name(self) -> str:
        return '📝 \t Неотвеченные отзывы по магазинам'

    def _set_next_state(self) -> str | None:
        return self.wb_cabinet.next_state

    def _set_reply_text(self) -> str:
        return self.wb_cabinet.reply_text

    def _set_children(self) -> list:
        return [button for button in self.wb_cabinet.children_buttons if button.class_name != 'GoToBack']

    # def _set_reply_text(self) -> str:
    #     return FACE_BOT + '<b>Выберите отзыв:</b>'
    #
    # async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
    #     reply_text, next_state = self.reply_text, self.next_state
    #     user_id = update.from_user.id
    #
    #     wb_user = self.dbase.wb_user_get_or_none(user_id=user_id)
    #     feedbacks = dict(list(wb_user.unanswered_feedbacks.items())[:NUM_FEED_BUTTONS])
    #     buttons = await self.utils_get_or_create_buttons(collection=feedbacks,
    #                                                      class_type='feedback',
    #                                                      update=update,
    #                                                      user_id=user_id)
    #     # print(buttons)
    #     self.children_buttons = buttons[:-1]
    #     result = await self.get_access_to_wb_api(update=update, state=state)
    #     if isinstance(result, tuple):
    #         reply_text, next_state = result
    #     else:
    #
    #         if suppliers_buttons := await self.api_suppliers_buttons_logic(update=update, state=state, user_id=user_id):
    #             self.children_buttons = suppliers_buttons
    #
    #             # [*suppliers_buttons, back_button]
    #             back_button = GoToBack(new=False)
    #             if not back_button in self.children_buttons:
    #                 self.children_buttons.append(back_button)
    #
    #     return reply_text, next_state


class MessageOnceForCreateResponseManuallyButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMMainMenuStates:create_response_manually'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Извините, произошла ошибка, попробуйте немного позже'

    def _set_next_state(self) -> str:
        return 'reset_state'

    async def _set_answer_logic(self, update, state) -> tuple[str | None, str | None]:
        wait_msg = await self.bot.send_message(chat_id=update.from_user.id,
                                               text=self.default_generate_answer)
        reply_text = 'Я сгенерировал ответ на отзыв:\n\n' + await self.ai.reply_feedback(feedback=update.text)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=wait_msg.message_id)

        return reply_text if reply_text else self.reply_text, self.next_state


class CreateResponseManually(BaseButton):

    def _set_name(self) -> str:
        return '✍ \t Сгенерировать текст по ключевикам'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Введите название товара и текст отзыва, я сгенерирую ответ' \
                          '\n\n<b>Пример:</b> Чехол на iPhone 11. Очень понравился чехол. ' \
                          'Мягкий, плотно сидит и хорошо защищает камеру.'

    def _set_next_state(self) -> str:
        return FSMMainMenuStates.create_response_manually

    def _set_messages(self) -> dict:
        message = MessageOnceForCreateResponseManuallyButton(self.button_id)
        return {message.state_or_key: message}


class AboutBot(BaseButton):

    def _set_name(self) -> str:
        return 'ℹ \t О боте'

    def _set_reply_text(self) -> str:
        return f"{FACE_BOT} Приветствую \t ✌️" \
               "\nЯ бот который призван помогать продавцам писать ответы на отзывы и тексты для карточек товаров. " \
               "Работаю с использованием технологий искусственного интеллекта ChatGPT. Прошу отнестись с пониманием " \
               "- я полностью бесплатный. Поэтому я иногда буду высылать анонсы полезных вебинаров для продавцов " \
               "Wildberries. У вас будет возможность просмотреть их и прокачать свои знания." \
               f"\n\nТехническая поддержка - {SUPPORT}" \
               "\n\nВступайте в наш телеграмм канал для продавцов Wildberries - https://t.me/marpla_wildberries" \
               "\n\nНаш YouTube канал с кучей полезной информации  - https://www.youtube.com/@marpla_ru"


class SupportButton(BaseButton):

    def _set_name(self) -> str:
        return '🆘 \t Поддержка'

    def _set_reply_text(self) -> str | None:
        return None

    def _set_url(self) -> str | None:
        return SUPPORT


class MainMenu(BaseButton):

    def _set_name(self) -> str:
        return 'ℹ \t Главное меню'  # 📒

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите один из пунктов главного меню:</b>'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [PersonalCabinet(parent_name=self.class_name, parent_button=self),
                AnswerManagement(parent_name=self.class_name, parent_button=self),
                CreateResponseManually(parent_name=self.class_name, parent_button=self),
                AboutBot(parent_name=self.class_name, parent_button=self),
                SupportButton(parent_name=self.class_name, parent_button=self)]
