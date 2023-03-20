from dataclasses import dataclass

# mode_work


@dataclass
class WPParseData:
    wb: str = 'https://www.wildberries.ru'
    wb_catalog: str = 'https://www.wildberries.ru/webapi/menu/main-menu-ru-ru.json'
