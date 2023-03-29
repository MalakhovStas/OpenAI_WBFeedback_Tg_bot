import asyncio
import json
import random
from typing import Iterable

import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType

from config import USE_PROXI, PROXI_FILE, TYPE_PROXI


class RequestsManager:

    __instance = None
    content_type = {"Content-Type": "application/json"}
    user_agent = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                                "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36;"}

    proxi_types = {'socks5': ProxyType.SOCKS5, 'socks4': ProxyType.SOCKS4,
                   'https': ProxyType.HTTPS, 'http': ProxyType.HTTP}

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, logger):
        self.logger = logger
        self.proxies = self.get_proxies()
        self.sign = self.__class__.__name__ + ': '

    async def __call__(self, url, headers: dict | None = None, method: str | None = None,
                       data: dict | list | None = None, list_requests: list | None = None,
                       add_headers: bool = False, step: int = 1) -> Iterable:
        """ Повторяет запрос/запросы, если сервер ответил error=True """

        if not headers:
            headers = self.content_type | self.user_agent
        elif headers and add_headers:
            headers = self.content_type | self.user_agent | headers
        if not method:
            method = 'get'
        if list_requests:
            result = await self.aio_request_gather(list_requests=list_requests,
                                                   headers=headers,
                                                   method=method,
                                                   data=data)
        else:
            result = await self.aio_request(
                url=url,
                headers=headers,
                method=method,
                data=data
            )
        if isinstance(result, dict) and result.get('error'):
            step = step + 1
            text = 'i try again call func aio_request because' if step < 3 else 'brake'
            self.logger.warning(self.sign + f'func __call__ {step=} -> {text} -> '
                                            f'{result.get("error")=} | {str(result)[:100]=}...')
            if step < 3:
                result = await self.__call__(url=url, headers=headers, method=method, data=data,
                                             list_requests=list_requests, add_headers=add_headers, step=step)
        else:
            self.logger.debug(self.sign + f'{step=} func __call__ return {type(result)=} | {len(result)=}')

        return result

    @staticmethod
    async def check_proxi(proxi):
        # TODO create logic checking proxi
        return True

    @staticmethod
    def get_proxies() -> list:
        with open(PROXI_FILE, 'r') as file:
            proxies = file.read().splitlines()
        return proxies if proxies else list()

    async def get_proxi(self):
        ip, port, login, password = None, None, None, None

        if USE_PROXI:
            proxi = random.choice(self.proxies)
            if await self.check_proxi(proxi):
                ip, port, login, password = proxi.split('\t')
                self.logger.debug(self.sign + f'\033[31mUSE PROXI -> '
                                              f'{ip=} | {port=} | {login=} | {password=} | {TYPE_PROXI=}\033[0m')
        return ip, port, login, password

    async def aio_request(self, url, headers, method: str = 'get', data: dict | None = None) -> dict | list:
        """ Повторяет запрос, если во время выполнения запроса произошло исключение из Exception"""
        step = 1
        result = dict()
        ip, port, login, password = await self.get_proxi()
        data = json.dumps(data) if isinstance(data, (dict, list)) else None
        self.logger.debug(self.sign+f'{step=} func aio_request -> sending request to: '
                                    f'{url=} | {method=} | {str(data)[:100]=}... | {str(headers)[:100]=}...')
        if ip and port and login and password:
            connector = ProxyConnector(
                proxy_type=self.proxi_types.get(TYPE_PROXI.lower()),
                host=ip,
                port=port,
                username=login,
                password=password,
                # rdns=True ???
            )
        else:
            connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            while step < 4:
                try:
                    if method == 'post':
                        async with session.post(url, data=data, ssl=False, timeout=20) as response:
                            if response.content_type in ['text/html', 'text/plain']:
                                result = {'response': await response.text()}
                            else:
                                result = await response.json()
                    elif method == 'patch':
                        async with session.patch(url, data=data, ssl=False, timeout=20) as response:
                            if response.content_type in ['text/html', 'text/plain']:
                                result = {'response': await response.text()}
                            else:
                                result = await response.json()

                    else:
                        async with session.get(url, ssl=False, timeout=20) as response:
                            if response.content_type in ['text/html', 'text/plain']:
                                result = {'response': await response.text()}
                            else:
                                result = await response.json()

                except Exception as exception:
                    text = f'try again' if step < 3 else 'brake requests return EMPTY DICT'
                    self.logger.warning(self.sign + f'{step=} | func=aio_request -> ERROR {exception=} '
                                                    f'| use {proxi=} -> {text}')
                    step += 1
                else:
                    self.logger.debug(self.sign + f'{step=} | func=aio_request return={str(result)[:100]}...')
                    break
        return result

    async def aio_request_gather(
            self, list_requests, headers, method: str = 'get', data: dict | None = None) -> Iterable:

        if method == 'post':
            task_data = [self.aio_request(url=url, headers=headers, method=method, data=data) for url in list_requests]
        else:
            task_data = [self.aio_request(url=url, headers=headers) for url in list_requests]
        list_result = await asyncio.gather(*task_data)
        await asyncio.sleep(0.1)
        return list_result
