
import copy

from buttons_and_messages.base_classes import Base


class ReloadDumpManager:
    """ Класс Singleton для создания json дампов БД и загрузки данных в БД из них"""
    __instance = None

    # file_dump_messages = 'database/dumps/messages.json'
    # file_dump_users = 'database/dumps/users.json'
    file_dump_general_collection = 'database/dumps/general_collection.json'

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, dbase, logger):
        self.dbase = dbase
        self.logger = logger
        self.sign = self.__class__.__name__+': '

    @staticmethod
    async def class_object_serializer(is_object):
        return {is_object.class_name: {attr: getattr(is_object, attr) for attr in is_object.__slots__}}

    async def load_general_collection(self):
        # collection = copy.deepcopy(Base.general_collection)
        ...
