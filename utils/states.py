from aiogram.dispatcher.filters.state import StatesGroup, State
""" Параметры машины состояний пользователя и администратора """


class FSMMainMenuStates(StatesGroup):
    main_menu = State()
    create_response_manually = State()
    submit_for_revision_task_response_manually = State()


class FSMPersonalCabinetStates(StatesGroup):
    personal_cabinet = State()
    enter_in_Wildberries = State()
    set_up_notifications = State()
    select_answer_mode = State()

    enter_signature = State()

    enter_yourself_set_up_notification_times = State()
    edit_feedback_answer = State()


class FSMUtilsStates(StatesGroup):
    message_after_user_enters_phone = State()
    message_after_user_enters_sms_code = State()
    enter_supplier_id_mode = State()


class FSMAdminStates(StatesGroup):
    password_mailing = State()
    mailing = State()
    mailing_admins = State()

    change_user_balance = State()
    change_user_requests_balance = State()
    block_user = State()
    unblock_user = State()
