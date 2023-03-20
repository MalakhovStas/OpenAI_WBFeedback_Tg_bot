async def check_data(data: str) -> str | None:
    """ Удаляет из строки data все символы из table_symbols на выходе только цифры или None"""
    ru_alphabet = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя'
    en_alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    any_symbols = ' ~`"\'@#№$:;.,%^&?*|()[]{}-=+<>/\\'
    table_symbols = ''.join([*ru_alphabet, *en_alphabet, *any_symbols])

    for sym in table_symbols:
        data = data.replace(sym, '')
    return data if data.isdigit() else None

