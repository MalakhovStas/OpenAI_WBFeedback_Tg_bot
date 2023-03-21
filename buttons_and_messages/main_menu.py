from buttons_and_messages.personal_cabinet import WildberriesCabinet, SetUpNotificationTimes, SignatureToTheAnswer, GoToBack
from config import SUPPORT, BOT_NIKNAME, FACE_BOT
from .base_classes import BaseButton, BaseMessage
from utils.states import FSMMainMenuStates, FSMPersonalCabinetStates


class PersonalCabinet(BaseButton):

    def _set_name(self) -> str:
        return '⚙ Личный кабинет'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите пункт меню:</b>'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.personal_cabinet

    def _set_children(self) -> list:
        return [WildberriesCabinet(parent_name=self.__class__.__name__),
                SetUpNotificationTimes(parent_name=self.__class__.__name__),
                SignatureToTheAnswer(parent_name=self.__class__.__name__)]


class AnswerManagement(BaseButton):

    def _set_name(self) -> str:
        return '📝 Посмотреть неотвеченные отзывы'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'У вас пока нет отзывов без ответа\n'

    async def _set_answer_logic(self, update, state):
        wb_cabinet = WildberriesCabinet(new=False)
        reply_text, next_state = await wb_cabinet._set_answer_logic(update, state)
        self.children_buttons = [button for button in wb_cabinet.children_buttons if button.class_name != 'GoToBack']
        return reply_text, next_state


class MessageOnceForCreateResponseManuallyButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMMainMenuStates:create_response_manually'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Извините, произошла ошибка, попробуйте немного позже'

    def _set_next_state(self) -> str:
        return 'reset_state'

    async def _set_answer_logic(self, update, state) -> tuple[str | None, str | None]:
        wait_msg = await self.bot.send_message(chat_id=update.from_user.id, text=self.default_generate_answer)
        reply_text = 'Я сгенерировал ответ на отзыв:\n\n' + await self.ai.reply_feedback(feedback=update.text)
        await self.bot.delete_message(chat_id=update.from_user.id, message_id=wait_msg.message_id)

        return reply_text if reply_text else self.reply_text, self.next_state


class CreateResponseManually(BaseButton):

    def _set_name(self) -> str:
        return '✍ Сгенерировать текст по ключевикам'

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
        return 'ℹ О боте'

    def _set_reply_text(self) -> str:
        return f"{FACE_BOT} Приветствую ✌️" \
               "\nЯ бот который призван помогать продавцам писать ответы на отзывы и тексты для карточек товаров. " \
               "Работаю с использованием технологий искусственного интеллекта ChatGPT. Прошу отнестись с пониманием " \
               "- я полностью бесплатный. Поэтому я иногда буду высылать анонсы полезных вебинаров для продавцов " \
               "Wildberries. У вас будет возможность просмотреть их и прокачать свои знания." \
               f"\n\nТехническая поддержка - {SUPPORT}" \
               "\n\nВступайте в наш телеграмм канал для продавцов Wildberries - https://t.me/marpla_wildberries" \
               "\n\nНаш YouTube канал с кучей полезной информации  - https://www.youtube.com/@marpla_ru"


class SupportButton(BaseButton):

    def _set_name(self) -> str:
        return '🆘 Поддержка'

    def _set_reply_text(self) -> str | None:
        return None

    def _set_url(self) -> str | None:
        return SUPPORT


class MainMenu(BaseButton):

    def _set_name(self) -> str:
        return 'ℹ Главное меню'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите один из пунктов главного меню:</b>'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [PersonalCabinet(parent_name=self.__class__.__name__),
                AnswerManagement(parent_name=self.__class__.__name__),
                CreateResponseManually(parent_name=self.__class__.__name__),
                AboutBot(parent_name=self.__class__.__name__),
                SupportButton(parent_name=self.__class__.__name__)]

