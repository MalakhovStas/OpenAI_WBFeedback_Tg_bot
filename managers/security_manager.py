import time
from collections import namedtuple

from aiogram.types import CallbackQuery, Message

from config import FLOOD_CONTROL_TIME, FLOOD_CONTROL_STOP_TIME, FLOOD_CONTROL_NUM_ALERTS


class SecurityManager:
    """ Класс Singleton обеспечивающий контроль доступа к боту и механизм защиты от флуда """
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, dbase, logger):
        self.dbase = dbase
        self.logger = logger
        self.__flood_control_data: dict = {}
        self.sign = self.__class__.__name__+': '

    async def update_informer(self, update: CallbackQuery | Message, user_data: dict | None) -> None:
        """ Логирование информации о входящем сообщении от пользователя"""
        state_user, data_user = await self.__get_data_from_user_data(update, user_data)

        message = f'incoming update -> {("callback:", update.data) if isinstance(update, CallbackQuery) else ("message:", update.text)}' \
                  f' -> from USER -> full_name: {update.from_user.full_name}, user_id: {update.from_user.id}, ' \
                  f'@username: {update.from_user.username}, state_user: {state_user}, data_user: {data_user}'

        self.logger.info(self.sign + message)

    @staticmethod
    async def __get_data_from_user_data(update: CallbackQuery | Message, user_data: dict | None) -> tuple:
        """ Метод представления данных в нужном виде """
        state_user = None
        data_user = None
        if user_data:
            if data := user_data.get(str(update.from_user.id)):
                state_user = data.get('state')
                data_user = data.get('data')
        return state_user, data_user

    async def check_user(self, update: CallbackQuery | Message, user_data: dict | None) -> bool:
        """ Для проверки пользователя на предмет блокировки или создания нового """
        await self.update_informer(update, user_data)

        user = self.dbase.get_or_create_user(update=update)  # Именно тут создаётся new user

        user_status = user.access if user else 'new user'
        if user_status == 'block':
            self.logger.warning(self.sign + f'user_status: {user_status.upper()} -> user: {update.from_user.id}')
            result = False
        else:
            self.logger.info(self.sign + f'user_status: {user_status.upper()} -> user: {update.from_user.id}')
            result = True

        return result

    async def flood_control(self, update: CallbackQuery | Message) -> str:
        """ Механизм защиты от флуда с возможностью временной блокировки пользователя """
        user_id = update.from_user.id
        FloodData = namedtuple('FloodData', ['last_time', 'num_alerts', 'time_block'])
        flood_data: FloodData | None = self.__flood_control_data.get(user_id)

        if not flood_data:
            self.__flood_control_data[user_id] = FloodData(time.time(), 0, 0)
            result = 'ok'

        else:
            if flood_data.time_block != 0 and flood_data.time_block - time.time() > 0:
                result = 'blocked'

            elif flood_data.num_alerts == FLOOD_CONTROL_NUM_ALERTS:
                flood_data = flood_data._replace(num_alerts=0, time_block=time.time() + FLOOD_CONTROL_STOP_TIME)
                result = 'block'

            elif time.time() - flood_data.last_time < FLOOD_CONTROL_TIME:
                flood_data = flood_data._replace(last_time=time.time(), num_alerts=flood_data.num_alerts + 1)
                result = 'bad'

            else:
                flood_data = flood_data._replace(last_time=time.time(), num_alerts=0)
                result = 'ok'

            self.__flood_control_data[user_id] = flood_data

        self.logger.info(self.sign + f'{result.upper()} -> flood control -> user: {user_id}')
        return result
