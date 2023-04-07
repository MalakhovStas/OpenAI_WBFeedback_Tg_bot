from buttons_and_messages.personal_cabinet import WildberriesCabinet, SetUpNotificationTimes, SignatureToTheAnswer
from config import SUPPORT, FACE_BOT, NUM_FEED_BUTTONS, DEFAULT_FEED_ANSWER
from utils.states import FSMMainMenuStates, FSMPersonalCabinetStates
from .base_classes import BaseButton, BaseMessage, Utils
from aiogram.types import CallbackQuery
from aiogram.dispatcher import FSMContext
from .stars_buttons import UnansweredFeedbackManagement


class PersonalCabinet(BaseButton):

    def _set_name(self) -> str:
        return '⚙ \t Личный кабинет'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите пункт меню:</b>'

    def _set_next_state(self) -> str:
        return FSMPersonalCabinetStates.personal_cabinet

    def _set_children(self) -> list:
        return [WildberriesCabinet(parent_name=self.class_name),
                UnansweredFeedbackManagement(parent_name=self.class_name),
                SetUpNotificationTimes(parent_name=self.class_name),
                SignatureToTheAnswer(parent_name=self.class_name)]


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
    #
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


class RegenerateAIResponse(BaseButton):

    def _set_name(self) -> str:
        return '🔁 \t Сгенерировать заново'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Извините, произошла ошибка, попробуйте немного позже'

    def _set_children(self) -> list:
        return [self, SubmitForRevisionTaskResponseManually(new=False),
                CreateNewTaskForResponseManually(new=False)]

    async def _set_answer_logic(self, update, state) -> tuple[str | tuple, str | None]:
        user_id = update.from_user.id
        # reply_text = 'Я сгенерировал текст:\n\n'
        reply_text = self.default_i_generate_text
        wait_msg = await self.bot.send_message(chat_id=user_id, text=self.default_generate_answer)

        if ai_messages_data := await self.button_search_and_action_any_collections(
                user_id=user_id, action='get', button_name='ai_messages_data', updates_data=True):

            ai_messages_data.pop(-1)  # выкидываем последнюю генерацию
            task_to_generate_ai = ai_messages_data.pop(-1).get('content')  # достаём задание - prompt

            ai_answer = await self.ai.some_question(prompt=task_to_generate_ai, messages_data=ai_messages_data)
        else:
            ai_answer = DEFAULT_FEED_ANSWER

        if ai_answer != DEFAULT_FEED_ANSWER:
            reply_text = reply_text + ai_answer + ':ai:some_question'
        else:
            self.children_buttons = []
            reply_text = self.reply_text

        await self.bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)

        return reply_text, self.next_state


class MessageOnceForSubmitForRevisionTaskResponseManuallyButton(BaseMessage):
    def _set_state_or_key(self) -> str:
        return 'FSMMainMenuStates:submit_for_revision_task_response_manually'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Извините, произошла ошибка, попробуйте немного позже'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [RegenerateAIResponse(new=False),
                SubmitForRevisionTaskResponseManually(new=False),
                CreateNewTaskForResponseManually(new=False)]

    async def _set_answer_logic(self, update, state) -> tuple[str | tuple, str | None]:
        # reply_text = 'Я сгенерировал текст:\n\n'
        reply_text = self.default_i_generate_text
        user_id = update.from_user.id
        task_to_revision_regenerate_ai = update.text.strip()

        ai_messages_data = await self.button_search_and_action_any_collections(
            user_id=user_id, action='get', button_name='ai_messages_data', updates_data=True)

        wait_msg = await self.bot.send_message(chat_id=user_id, text=self.default_generate_answer)

        ai_answer = await self.ai.some_question(prompt=task_to_revision_regenerate_ai, messages_data=ai_messages_data)

        if ai_answer != DEFAULT_FEED_ANSWER:
            reply_text = reply_text + ai_answer + ':ai:some_question'

        else:
            self.children_buttons = []
            reply_text = self.reply_text

        await self.bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)

        return reply_text, self.next_state


class SubmitForRevisionTaskResponseManually(BaseButton):
    def _set_name(self) -> str:
        return '🗒 \t  Отправить на доработку'

    def _set_reply_text(self) -> str:
        return FACE_BOT + ' Напишите, что именно нужно доработать?' \
                          '\n\n<b>Пример:</b> Укажи больше информации о предназначении куртки.'

    def _set_next_state(self) -> str:
        return FSMMainMenuStates.submit_for_revision_task_response_manually

    def _set_messages(self) -> dict:
        message = MessageOnceForSubmitForRevisionTaskResponseManuallyButton(parent_name=self.class_name)
        return {message.state_or_key: message}


class CreateNewTaskForResponseManually(BaseButton):
    def _set_name(self) -> str:
        return '📝 \t Новое задание'

    async def _set_answer_logic(self, update, state) -> tuple[str | tuple, str | None]:
        logic_button = CreateResponseManually(new=False)
        return logic_button.reply_text, logic_button.next_state


class MessageOnceForCreateResponseManuallyButton(BaseMessage):

    def _set_state_or_key(self) -> str:
        return 'FSMMainMenuStates:create_response_manually'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'Извините, произошла ошибка, попробуйте немного позже'

    def _set_next_state(self) -> str:
        return 'reset_state'

    def _set_children(self) -> list:
        return [RegenerateAIResponse(parent_name=self.class_name, parent_button=self),
                SubmitForRevisionTaskResponseManually(parent_name=self.class_name, parent_button=self),
                CreateNewTaskForResponseManually(parent_name=self.class_name, parent_button=self)]

    async def _set_answer_logic(self, update, state) -> tuple[str | tuple, str | None]:
        # reply_text = 'Я сгенерировал текст:\n\n'
        reply_text = self.default_i_generate_text
        user_id = update.from_user.id
        task_to_generate_ai = update.text.strip()
        wait_msg = await self.bot.send_message(chat_id=user_id, text=self.default_generate_answer)

        ai_messages_data = await self.button_search_and_action_any_collections(
            user_id=user_id, action='add', button_name='ai_messages_data',
            instance_button=list(), updates_data=True)

        ai_answer = await self.ai.some_question(prompt=task_to_generate_ai, messages_data=ai_messages_data)

        if ai_answer != DEFAULT_FEED_ANSWER:
            reply_text = reply_text + ai_answer + ':ai:some_question'

        else:
            self.children_buttons = []
            reply_text = self.reply_text

        await self.bot.delete_message(chat_id=user_id, message_id=wait_msg.message_id)

        return reply_text, self.next_state


class CreateResponseManually(BaseButton):

    def _set_name(self) -> str:
        return '✍ \t Сгенерировать текст по ключевикам'

    def _set_reply_text(self) -> str:
        return FACE_BOT + 'О чём мне написать текст?' \
                          '\n\n<b>Пример:</b> Напиши продающий текст с использованием слов: ' \
                          'платье, большое, черное, лето, длинное.'

    def _set_next_state(self) -> str:
        return FSMMainMenuStates.create_response_manually

    def _set_messages(self) -> dict:
        message = MessageOnceForCreateResponseManuallyButton(parent_name=self.class_name)
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
        return [PersonalCabinet(parent_name=self.class_name),
                # AnswerManagement(parent_name=self.class_name),
                # UnansweredFeedbackManagement(parent_name=self.class_name),
                CreateResponseManually(parent_name=self.class_name),
                AboutBot(parent_name=self.class_name),
                SupportButton(parent_name=self.class_name)]
