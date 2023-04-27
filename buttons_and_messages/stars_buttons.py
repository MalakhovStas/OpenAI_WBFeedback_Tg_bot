from buttons_and_messages.base_classes import BaseButton, Utils, GoToBack
from buttons_and_messages.personal_cabinet import SelectAPIMode, SelectSupplierIDMode
from aiogram.types import CallbackQuery, Message
from aiogram.dispatcher import FSMContext
from config import FACE_BOT, NUM_FEED_BUTTONS


class SubButtonOneStarFeeds(BaseButton, Utils):
    num_stars = 1

    def _set_name(self) -> str:
        return f'1 звезда'

    def _set_reply_text(self) -> str | None:
        return self.default_choice_feedback


class SubButtonTwoStarFeeds(BaseButton):
    num_stars = 2

    def _set_name(self) -> str:
        return f'2 звезды'

    def _set_reply_text(self) -> str | None:
        return self.default_choice_feedback


class SubButtonThreeStarFeeds(BaseButton):
    num_stars = 3

    def _set_name(self) -> str:
        return f'3 звезды'

    def _set_reply_text(self) -> str | None:
        return self.default_choice_feedback


class SubButtonFourStarFeeds(BaseButton):
    num_stars = 4

    def _set_name(self) -> str:
        return f'4 звезды'

    def _set_reply_text(self) -> str | None:
        return self.default_choice_feedback


class SubButtonFiveStarFeeds(BaseButton):
    num_stars = 5

    def _set_name(self) -> str:
        return f'5 звезд'

    def _set_reply_text(self) -> str | None:
        return self.default_choice_feedback


class UnansweredFeedbackManagement(BaseButton, Utils):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.children_list = [SubButtonOneStarFeeds(parent_name=self.class_name, parent_button=self),
                              SubButtonTwoStarFeeds(parent_name=self.class_name, parent_button=self),
                              SubButtonThreeStarFeeds(parent_name=self.class_name, parent_button=self),
                              SubButtonFourStarFeeds(parent_name=self.class_name, parent_button=self),
                              SubButtonFiveStarFeeds(parent_name=self.class_name, parent_button=self)]

    def _set_name(self) -> str:
        return '📝 \t Неотвеченные отзывы'

    def _set_reply_text(self) -> str:
        return FACE_BOT + '<b>Выберите:</b>'

    async def __logic_set_childrens(self, button, feeds_by_stars, update, state, user_id):
        # print(feeds_by_stars)
        try:
            buttons = await self.utils_get_or_create_buttons(
                collection=dict(list(feeds_by_stars.items())[:NUM_FEED_BUTTONS]),
                class_type='Feedback', update=update, user_id=user_id)
        except AttributeError as exc:
            # print('exc', exc)
            buttons = list()
            await SelectAPIMode(new=False)._set_answer_logic(update=update, state=state)
            await SelectSupplierIDMode(new=False)._set_answer_logic(update=update, state=state)
            await self.__logic_set_childrens(button=button, feeds_by_stars=feeds_by_stars,
                                             update=update, state=state, user_id=user_id)

        if not len(buttons) <= 1:
            button.children_buttons = buttons
            self.children_buttons.append(button)

    async def _set_answer_logic(self, update: CallbackQuery, state: FSMContext):
        self.children_buttons = list()
        go_to_back = GoToBack(new=False)
        user_id = update.from_user.id

        # api_suppliers = await self.api_suppliers_buttons_logic(update=update, state=state, user_id=user_id)
        # id_suppliers = await self.parsing_suppliers_buttons_logic(update=update, state=state, user_id=user_id)

        wb_user = await self.dbase.wb_user_get_or_none(user_id=user_id)

        feeds_by_1_stars = dict()
        feeds_by_2_stars = dict()
        feeds_by_3_stars = dict()
        feeds_by_4_stars = dict()
        feeds_by_5_stars = dict()

        for feed_key_name, feed_data in wb_user.unanswered_feedbacks.items():
            if feed_data.get('productValuation') == 1:
                feeds_by_1_stars.update({feed_key_name: feed_data})

            elif feed_data.get('productValuation') == 2:
                feeds_by_2_stars.update({feed_key_name: feed_data})

            elif feed_data.get('productValuation') == 3:
                feeds_by_3_stars.update({feed_key_name: feed_data})

            elif feed_data.get('productValuation') == 4:
                feeds_by_4_stars.update({feed_key_name: feed_data})

            elif feed_data.get('productValuation') == 5:
                feeds_by_5_stars.update({feed_key_name: feed_data})

        for chbtn in self.children_list:
            if chbtn.class_name == 'SubButtonOneStarFeeds':
                chbtn.name = f'⭐ \t 1 звезда 〔 {len(feeds_by_1_stars)} 〕'
                await self.__logic_set_childrens(button=chbtn, feeds_by_stars=feeds_by_1_stars,
                                                 update=update, state=state, user_id=user_id)

            elif chbtn.class_name == 'SubButtonTwoStarFeeds':
                chbtn.name = f'⭐ \t 2 звезды 〔 {len(feeds_by_2_stars)} 〕'
                await self.__logic_set_childrens(button=chbtn, feeds_by_stars=feeds_by_2_stars,
                                                 update=update, state=state, user_id=user_id)

            elif chbtn.class_name == 'SubButtonThreeStarFeeds':
                chbtn.name = f'⭐ \t 3 звезды 〔 {len(feeds_by_3_stars)} 〕'
                await self.__logic_set_childrens(button=chbtn, feeds_by_stars=feeds_by_3_stars,
                                                 update=update, state=state, user_id=user_id)

            elif chbtn.class_name == 'SubButtonFourStarFeeds':
                chbtn.name = f'⭐ \t 4 звезды 〔 {len(feeds_by_4_stars)} 〕'
                await self.__logic_set_childrens(button=chbtn, feeds_by_stars=feeds_by_4_stars,
                                                 update=update, state=state, user_id=user_id)

            elif chbtn.class_name == 'SubButtonFiveStarFeeds':
                chbtn.name = f' ⭐ \t 5 звезд 〔 {len(feeds_by_5_stars)} 〕'
                await self.__logic_set_childrens(button=chbtn, feeds_by_stars=feeds_by_5_stars,
                                                 update=update, state=state, user_id=user_id)

        self.children_buttons.append(go_to_back) if not go_to_back in self.children_buttons else None
        reply_text = self.default_not_feeds_in_supplier if len(self.children_buttons) <= 1 else self.reply_text
        return reply_text, self.next_state
