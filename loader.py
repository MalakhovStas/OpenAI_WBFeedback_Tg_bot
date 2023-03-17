from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from loguru import logger
from pyqiwip2p import AioQiwiP2P

from config import BOT_TOKEN, QIWI_PRIV_KEY, LOGGER_ERRORS, LOGGER_DEBUG
from managers.db_manager import DBManager
from managers.openai_manager import OpenAIManager
# from managers.reload_dump_manager import ReloadDumpManager
from managers.security_manager import SecurityManager
from managers.admins_manager import AdminsManager
from managers.answer_logic_manager import AnswerLogicManager
from buttons_and_messages.base_classes import Base
from managers.requests_manager import RequestsManager
from managers.wildberries_api_manager import WBAPIManager
""" Модуль загрузки основных инструментов приложения """

logger.add(**LOGGER_ERRORS)
logger.add(**LOGGER_DEBUG)

dbase = DBManager(logger=logger)
security = SecurityManager(dbase=dbase, logger=logger)  # должен быть первым из менеджеров


bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# p2p = AioQiwiP2P(auth_key=QIWI_PRIV_KEY)
# rdm = ReloadDumpManager(dbase=dbase, logger=logger)

rm = RequestsManager(logger=logger)
ai = OpenAIManager(logger=logger)
adm = AdminsManager(bot=bot, logger=logger, dbase=dbase)
alm = AnswerLogicManager(ai=ai, bot=bot, logger=logger)
wb_api = WBAPIManager(dbase=dbase, rm=rm, ai=ai, logger=logger)

Base.ai, Base.bot, Base.wb_api = ai, bot, wb_api

