import asyncio
from asyncio.exceptions import TimeoutError

import openai
from typing import Sequence
# from utils.admins_send_message import func_admins_message

from config import OpenAI_TOKEN, OpenAI_TIMEOUT, SUPPORT


class OpenAIManager:
    """ Класс Singleton для работы с API ChatGPT """
    __instance = None
    # __default_bad_answer = 'При генерации ответа произошла ошибка <b>{exc}</b>, попробуйте сгенерировать ' \
    #                        f'новый ответ, или обратитесь в поддержку: {SUPPORT}'

    # __default_bad_answer = 'При генерации ответа произошла ошибка, попробуйте сгенерировать ' \
    #                        f'новый ответ, или обратитесь в поддержку:' + \
    #                        f'@{SUPPORT.lstrip("https://t.me/")}'

    __default_bad_answer = 'При генерации ответа произошла ошибка {exc}, попробуйте сгенерировать новый ответ'

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __init__(self, logger):
        self.openai = openai
        self.openai.api_key = OpenAI_TOKEN
        self.logger = logger
        self.sign = self.__class__.__name__+': '

    async def answer(self, prompt: str) -> str:
        """ Запрос к ChatGPT"""
        self.logger.info(self.sign + f"question: {prompt[:100]}...")

        try:
            response = await asyncio.wait_for(self.openai.Completion.acreate(
                model="text-davinci-003",
                prompt=prompt,
                # temperature=0.9,
                temperature=0,
                max_tokens=1800,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                timeout=OpenAI_TIMEOUT
            ), timeout=OpenAI_TIMEOUT + 3)

            # print(response)
            if response and isinstance(response.get('choices'), Sequence):
                answer = response['choices'][0]['text'].strip('\n')
            else:
                answer = self.__default_bad_answer.format(exc='')

        except Exception as exception:
            # TODO Разобраться с циркулярным импортом
            # await func_admins_message(exc=exception)
            self.logger.warning(self.sign + f"{exception=}")
            # TODO Убрать сообщение об исключении пользователю
            answer = self.__default_bad_answer.format(exc=exception.__class__.__name__)
            # answer = self.__default_bad_answer

        text = answer.replace('\n', '')
        self.logger.info(self.sign + f"answer: {text[:100]}...")
        return answer

    async def generate_image_from_text(self, prompt):
        """ Сгенерированные изображения могут иметь размер 256x256, 512x512 или 1024x1024 пикселей.
        Меньшие размеры генерируются быстрее. Вы можете запросить от 1 до 10 изображений за раз,
        используя параметр n """

        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response['data'][0]['url']
        return image_url

    @classmethod
    async def _check_type_str(cls, *args) -> bool:
        return all((isinstance(arg, str) for arg in args))

    async def reply_feedback(self, feedback: str) -> str:
        if await self._check_type_str(feedback):
            #TODO Разобраться почему я так написал feedback[:100]
            return await self.answer(f'напиши ответ на отзыв: {feedback}')

    async def reply_many_feedbacks(self, feed_name: str, feedback: str) -> tuple:
        answer = None
        if await self._check_type_str(feedback):
            #TODO Разобраться почему я так написал feedback[:100]
            answer = await self.answer(f'напиши ответ на отзыв: {feedback}')
        return feed_name, answer

    async def some_question(self, prompt: str) -> str:
        if await self._check_type_str(prompt):
            return await self.answer(prompt)


# Так выглядит ответ
# {
#   "choices": [
#     {
#       "finish_reason": "stop",
#       "index": 0,
#       "logprobs": null,
#       "text": "\u0430\u0442\u0435\u0440\u0438\u0430\u043b \u043f\u0440\u0438\u044f\u0442\u043d\u044b\u0439.\n\n\u0421\u043f\u0430\u0441\u0438\u0431\u043e \u0437\u0430 \u0412\u0430\u0448 \u043e\u0442\u0437\u044b\u0432! \u041c\u044b \u0440\u0430\u0434\u044b, \u0447\u0442\u043e \u0412\u0430\u043c \u043f\u043e\u043d\u0440\u0430\u0432\u0438\u043b\u0430\u0441\u044c \u043a\u0443\u0440\u0442\u043a\u0430 \u0434\u043b\u044f \u0412\u0430\u0448\u0435\u0439 \u0434\u043e\u0447\u0435\u0440\u0438. \u041c\u044b \u043f\u043e\u0441\u0442\u0430\u0440\u0430\u043b\u0438\u0441\u044c \u0441\u0434\u0435\u043b\u0430\u0442\u044c \u0432\u0441\u0435 \u043c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u043e \u043a\u0430\u0447\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e, \u0447\u0442\u043e\u0431\u044b \u0412\u0430\u043c \u0431\u044b\u043b\u043e \u0434\u043e\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u043e \u0443\u0434\u043e\u0432\u043e\u043b\u044c\u0441\u0442\u0432\u0438\u0435 \u043e\u0442 \u043f\u043e\u043a\u0443\u043f\u043a\u0438. \u0411\u043b\u0430\u0433\u043e\u0434\u0430\u0440\u0438\u043c \u0412\u0430\u0441 \u0437\u0430 \u0434\u043e\u0432\u0435\u0440\u0438\u0435 \u0438 \u0436\u0435\u043b\u0430\u0435\u043c \u0412\u0430\u043c \u043f\u0440\u0438\u044f\u0442\u043d\u044b\u0445 \u043f\u043e\u043a\u0443\u043f\u043e\u043a!"
#     }
#   ],
#   "created": 1679239442,
#   "id": "cmpl-6vpB47cqEu53oWtRauBAbZ5IVK2cS",
#   "model": "text-davinci-003",
#   "object": "text_completion",
#   "usage": {
#     "completion_tokens": 270,
#     "prompt_tokens": 134,
#     "total_tokens": 404
#   }
# }