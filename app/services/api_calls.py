import os
import json
import base64
import logging
import aiohttp
import asyncio
from typing import Optional, Tuple

from app.settings import YOUR_SITE_URL, BOT_NAME, VISION_MODEL

logger = logging.getLogger(__name__)

class FusionBrainGenerator:
    def __init__(self):
        self.url = 'https://api-key.fusionbrain.ai/'
        self.headers = {
            'X-Key': f'Key {os.getenv("FUSIONBRAIN_API_KEY")}',
            'X-Secret': f'Secret {os.getenv("FUSIONBRAIN_SECRET_KEY")}',
        }
        self.pipeline_id = None

    async def get_pipeline(self) -> Optional[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url + 'key/api/v1/pipelines', headers=self.headers, timeout=10) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if not data:
                        logger.error("No available pipelines")
                        return None
                    self.pipeline_id = data[0]['id']
                    return self.pipeline_id
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return None

    async def generate(self, prompt: str, style: str = None) -> Optional[str]:
        try:
            if not self.pipeline_id:
                await self.get_pipeline()
                if not self.pipeline_id:
                    return None

            params = {
                "type": "GENERATE",
                "numImages": 1,
                "width": 1024,
                "height": 1024,
                "generateParams": {
                    "query": prompt[:1000]
                }
            }

            if style and style != "DEFAULT":
                params["style"] = style

            form_data = aiohttp.FormData()
            form_data.add_field('pipeline_id', self.pipeline_id)
            form_data.add_field('params', json.dumps(params, ensure_ascii=False), content_type='application/json')

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.url + 'key/api/v1/pipeline/run',
                    headers=self.headers,
                    data=form_data,
                    timeout=30
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

            if 'uuid' not in data:
                logger.error("No UUID in response")
                return None

            return data['uuid']

        except Exception as e:
            logger.error(f"Generation error: {e}")
            return None

    async def check_generation(self, request_id: str, attempts: int = 15, delay: int = 5) -> Optional[Tuple[bytes, bool]]:
        try:
            while attempts > 0:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        self.url + 'key/api/v1/pipeline/status/' + request_id,
                        headers=self.headers,
                        timeout=10
                    ) as response:
                        data = await response.json()

                if data['status'] == 'DONE':
                    image_base64 = data['result']['files'][0]
                    censored = data['result'].get('censored', False)
                    return base64.b64decode(image_base64), censored
                elif data['status'] == 'FAIL':
                    error = data.get('errorDescription', 'Unknown error')
                    logger.error(f"Generation failed: {error}")
                    return None, False

                attempts -= 1
                await asyncio.sleep(delay)

            logger.error("Generation timeout")
            return None, False

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return None, False

class ImageAnalyzer:
    @staticmethod
    async def analyze(image_bytes: bytes, prompt: str = "Опиши изображение подробно на русском") -> str:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
                        'HTTP-Referer': YOUR_SITE_URL,
                        'X-Title': BOT_NAME,
                    },
                    json={
                        'model': VISION_MODEL,
                        'messages': [
                            {
                                'role': 'user',
                                'content': [
                                    {'type': 'text', 'text': prompt},
                                    {
                                        'type': 'image_url',
                                        'image_url': {
                                            'url': f'data:image/jpeg;base64,{base64.b64encode(image_bytes).decode("utf-8")}'
                                        }
                                    }
                                ]
                            }
                        ],
                        'max_tokens': 1000
                    },
                    timeout=30
                ) as response:
                    if response.status != 200:
                        data = await response.json()
                        error_msg = data.get('error', {}).get('message', 'Неизвестная ошибка API')
                        logger.error(f"Vision API Error: {error_msg}")
                        return f"❌ Ошибка анализа изображения: {error_msg}"

                    data = await response.json()
                    return data['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            return f"❌ Ошибка: {str(e)}"
