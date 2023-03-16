import openai
from config import OpenAI_TOKEN


class OpenAIManager:
    """ Класс Singleton для работы с API ChatGPT """
    __instance = None

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
        self.logger.info(self.sign + f"question: {prompt}")
        response = await self.openai.Completion.acreate(
          model="text-davinci-003",
          prompt=prompt,
          temperature=0.9,
          max_tokens=1800,
          top_p=1,
          frequency_penalty=0,
          presence_penalty=0
        )
        answer = response['choices'][0]['text'].lstrip('\n')
        self.logger.info(self.sign + f"answer: {answer}")
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
            return await self.answer(f'Напиши ответ на отзыв: {feedback}')

    async def reply_many_feedbacks(self, feed_name: str, feedback: str) -> tuple:
        answer = None
        if await self._check_type_str(feedback):
            answer = await self.answer(f'Напиши ответ на отзыв: {feedback}')
        return feed_name, answer

    async def some_question(self, prompt: str) -> str:
        if await self._check_type_str(prompt):
            return await self.answer(prompt)
