import os
import ast
from datetime import datetime

from dotenv import load_dotenv, find_dotenv

""" Модуль основной конфигурации приложения """

if not find_dotenv():
    exit('Переменные окружения не загружены т.к отсутствует файл .env\n'
         'Необходимо верно заполнить данные в файле .env.template и переименовать его в .env')
else:
    load_dotenv()


""" Количество перезапусков бота в случае падения """
MAX_RESTART_BOT = 3

""" Токен и имя телеграм бота """
BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_NIKNAME = os.getenv('BOT_NIKNAME')
FACE_BOT = '🤖 \t '
# FACE_BOT = ''

""" Режим генерации отзывов 'automatic' / 'manual'"""
# MODE_GENERATE_ANSWER = 'automatic'
MODE_GENERATE_ANSWER = 'manual'

# """ Ответ по умолчанию, обязательно должен начинаться с символа переноса строки - \n """
""" Ответ по умолчанию """
DEFAULT_FEED_ANSWER = ' \t Cгенерируйте ответ кнопкой\n \t "Сгенерировать ответ"\n\n' \
                      ' \t или введите ответ вручную по кнопке\n \t "Редактировать ответ"'

""" Токен ChatGPT и настройки таймаут для openai """
OpenAI_TOKEN = os.getenv('OPENAI_API_KEY')
OpenAI_ORGANIZATION = os.getenv('OPENAI_ORGANIZATION')

""" QIWI """
# https://developer.qiwi.com/ru/payments/#test_data_card
# https://pyqiwip2p.readthedocs.io/ru/latest/Use.html#id3
QIWI_PRIV_KEY = os.getenv('QIWI_PRIV_KEY')
LIFETIME = 5

""" Список администраторов и ссылка на чат поддержки """
ADMINS = os.getenv('ADMINS').split(', ') if os.getenv('ADMINS') else tuple()
TECH_ADMINS = os.getenv('TECH_ADMINS').split(', ') if os.getenv('TECH_ADMINS') else tuple()
SUPPORT = os.getenv('SUPPORT')

""" Команды бота """
DEFAULT_COMMANDS = (
    ('start', 'запустить бота'),
    ('my_shops', 'Мои магазины'),
    ('add_shop', 'Добавить магазин'),
    ('advert_bid_bot', 'Бот ставок'),
    ('bot_pos', 'Бот позиций'),
    ('school', 'Школа')
)

ADVERT_BID_BOT = 'https://t.me/AdsWbbot'
BOT_POS = 'https://t.me/WBpositionTOP_bot'
SCHOOL = 'https://marpla.pro/courses'

""" Конфигурация базы данных """
if not os.getenv('PG_DATABASE'):
    # DATABASE_CONFIG = ('sqlite', {'database': 'database/database.db'})
    DATABASE_CONFIG = ('sqlite', {'database': 'database/database.db',
                                  'pragmas': (('cache_size', -1024 * 64),
                                              ('journal_mode', 'wal'), ('foreign_keys', 1))})
else:
    DATABASE_CONFIG = ('postgres', ast.literal_eval(os.getenv('PG_DATABASE')))


""" Конфигурация логирования """

errors_format = '{time:DD-MM-YYYY at HH:mm:ss} | {level: <8} | {file: ^20} | {message}'
debug_format = '{time:DD-MM-YYYY at HH:mm:ss} | {level: <8} | file: {file: ^30} | ' \
               'func: {function: ^30} | line: {line: >3} | message: {message}'

logger_common_args = {
    'diagnose': True,
    'backtrace': False,
    'rotation': '10 Mb',
    'retention': 1,
    'compression': 'zip'
}

PATH_FILE_DEBUG_LOGS = 'logs/debug.log'
PATH_FILE_ERRORS_LOGS = 'logs/errors.log'

LOGGER_DEBUG = {'sink': PATH_FILE_DEBUG_LOGS, 'level': 'DEBUG', 'format': debug_format} | logger_common_args
LOGGER_ERRORS = {'sink': PATH_FILE_ERRORS_LOGS, 'level': 'WARNING', 'format': errors_format} | logger_common_args


""" Файл информации о пользователях по команде admin """
PATH_USERS_INFO = 'users_info.xlsx'

""" Включение / отключение механизма защиты от флуда """
FLOOD_CONTROL = True

""" Время между сообщениями от пользователя для защиты от флуда в секундах """
FLOOD_CONTROL_TIME = 0.3

""" Количество предупреждений перед блокировкой для защиты от флуда"""
FLOOD_CONTROL_NUM_ALERTS = 10

""" Время остановки обслуживания пользователя для защиты от флуда в секундах """
FLOOD_CONTROL_STOP_TIME = 60

""" Количество(+общее(игнор + не отв) кол-во в БД) запрашиваемых отзывов в одном запросе к Wildberries"""
WB_TAKE = 150
# WB_TAKE = 5

""" Отображаемое кол-во отзывов на кнопке supplier 'all' / '99+' """
NUM_FEEDS_ON_SUPPLIER_BUTTON = '99+'
# NUM_FEEDS_ON_SUPPLIER_BUTTON = 'all'

""" Настройка планировщика задач apscheduler, время между запуском 
    AutoUpdateFeedbackManager -> finding_unanswered_feedbacks - интервал обновления отзывов """
AUFM_INTERVAL_SECONDS = 2*60*60  # каждые 2 часа
# AUFM_INTERVAL_SECONDS = 60

""" Только отзывы этой даты попадут в автоматические уведомления формат: 2023 или 2023-03 или 2023-03-18"""
AUFM_ONLY_DATE = datetime.now().strftime('%Y-%m-%d')
# AUFM_ONLY_DATE = datetime.now().strftime('%Y-%m')


""" Количество кнопок-отзывов для вывода пользователю вне зависимости от их кол-ва в БД """
NUM_FEED_BUTTONS = 10

""" Настройки прокси """
USE_PROXI = True
PROXI_FILE = 'proxi.txt'
TYPE_PROXI = 'SOCKS5'
