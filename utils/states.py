from aiogram.dispatcher.filters.state import StatesGroup, State
""" Параметры машины состояний пользователя и администратора """


class FSMMainMenuStates(StatesGroup):
    main_menu = State()
    create_response_manually = State()


class FSMPersonalCabinetStates(StatesGroup):
    personal_cabinet = State()
    enter_in_Wildberries = State()
    set_up_notifications = State()
    select_answer_mode = State()
    signature_to_the_answer = State()
    signature_to_the_answer_enter_code_from_sms = State()
    enter_signature = State()
    enter_in_wildberries_cabinet = State()
    wildberries_cabinet_enter_code_from_sms = State()
    enter_yourself_set_up_notification_times = State()
    edit_feedback_answer = State()


class FSMAdminStates(StatesGroup):
    password_mailing = State()
    mailing = State()
    mailing_admins = State()

    change_user_balance = State()
    block_user = State()
    unblock_user = State()
