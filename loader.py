# from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
# from pyqiwip2p import AioQiwiP2P

from config import BOT_TOKEN, QIWI_PRIV_KEY, LOGGER_ERRORS, LOGGER_DEBUG, AUFM_INTERVAL_SECONDS
from managers.async_db_manager import DBManager
from managers.openai_manager import OpenAIManager
from managers.reload_dump_manager import ReloadDumpManager
# from managers.reload_dump_manager import ReloadDumpManager
from managers.security_manager import SecurityManager
from managers.admins_manager import AdminsManager
from managers.answer_logic_manager import AnswerLogicManager
from buttons_and_messages.base_classes import Base
from managers.requests_manager import RequestsManager
from managers.wildberries_api_manager import WBAPIManager
from managers.auto_update_feedback_manager import AutoUpdateFeedbackManager
from managers.wildberries_parsing_manager import WBParsingManager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from managers.prodamus_manager import ProdamusManager
""" Модуль загрузки основных инструментов приложения """

logger.add(**LOGGER_ERRORS)
logger.add(**LOGGER_DEBUG)

dbase = DBManager()
security = SecurityManager(dbase=dbase, logger=logger)  # должен быть первым из менеджеров

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# p2p = AioQiwiP2P(auth_key=QIWI_PRIV_KEY)
rdm = ReloadDumpManager(dbase=dbase, logger=logger)

rm = RequestsManager(logger=logger)
pay_sys = ProdamusManager(rm=rm, dbase=dbase, logger=logger)
ai = OpenAIManager(dbase=dbase, bot=bot, logger=logger)
adm = AdminsManager(bot=bot, logger=logger, dbase=dbase, rm=rm)

wb_api = WBAPIManager(dbase=dbase, rm=rm, ai=ai, logger=logger)
wb_parsing = WBParsingManager(dbase=dbase, bot=bot, rm=rm, ai=ai, logger=logger)

alm = AnswerLogicManager(ai=ai, bot=bot, logger=logger)

Base.ai, Base.bot, Base.wb_api, Base.wb_parsing, Base.pay_sys = ai, bot, wb_api, wb_parsing, pay_sys

scheduler = AsyncIOScheduler()

aufm = AutoUpdateFeedbackManager(dbase=dbase, storage=storage, bot=bot, wb_api=wb_api,
                                 wb_parsing=wb_parsing, alm=alm, logger=logger)

# start_time_scheduler = datetime.now() + timedelta(seconds=5)
# scheduler.add_job(aufm.finding_unanswered_feedbacks, trigger='interval',
#                   next_run_time=start_time_scheduler, seconds=AUFM_INTERVAL_SECONDS)

scheduler.add_job(aufm.finding_unanswered_feedbacks, trigger='interval', seconds=AUFM_INTERVAL_SECONDS)
