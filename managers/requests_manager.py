import asyncio
import json
import random

import aiohttp
from aiohttp_proxy import ProxyConnector, ProxyType

from config import USE_PROXI, PROXI_FILE, PROXI_PORT, PROXI_LOGIN, PROXI_PASSWORD, TYPE_PROXI


class RequestsManager:
    # TODO add proxi checker

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
                       data: dict | list | None = None, list_requests: list | None = None, add_headers: bool = False):
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
        return result

    @staticmethod
    def get_proxies() -> list:
        with open(PROXI_FILE, 'r') as file:
            proxies = file.read().splitlines()
        return proxies if proxies else list()

    async def check_proxi(self, proxi):
        # TODO create logic
        return True

    async def get_proxi(self):
        if not USE_PROXI:
            return list()
        proxi = random.choice(self.proxies)
        if await self.check_proxi(proxi):
            self.logger.debug(self.sign + f'use proxi: {proxi}')
            return proxi

    async def aio_request(self, url, headers, method: str = 'get', data: dict | None = None) -> dict | list | None:
        step = 1
        result = None
        proxi = await self.get_proxi()
        data = json.dumps(data) if isinstance(data, (dict, list)) else None
        if proxi:
            connector = ProxyConnector(
                proxy_type=self.proxi_types.get(TYPE_PROXI.lower()),
                host=proxi,
                port=PROXI_PORT,
                username=PROXI_LOGIN,
                password=PROXI_PASSWORD,
                # rdns=True ???
            )
        else:
            connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
            while step < 4:
                try:
                    if method == 'post':
                        async with session.post(url, data=data, ssl=False, timeout=20) as response:
                            if response.content_type == 'text/html':
                                result = {'response': await response.text()}
                            else:
                                result = await response.json()
                    else:
                        async with session.get(url, ssl=False, timeout=20) as response:
                            if response.content_type == 'text/html':
                                result = {'response': await response.text()}
                            else:
                                result = await response.json()

                except Exception as exc:
                    text = f'try again' if step < 3 else 'brake'
                    self.logger.warning(self.sign + f'request ERROR proxi: {proxi}, '
                                                    f'exception: {exc} -> step: {step} -> {text}')
                    step += 1
                else:
                    break

        return result

    async def aio_request_gather(self, list_requests, headers, method: str = 'get', data: dict | None = None):
        if method == 'post':
            task_data = [self.aio_request(url=url, headers=headers, method=method, data=data) for url in list_requests]
        else:
            task_data = [self.aio_request(url=url, headers=headers) for url in list_requests]
        list_result = await asyncio.gather(*task_data)
        await asyncio.sleep(0.1)
        return list_result
