from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("developer_landing.contact")

CLASSIFY_PROMPT = """
Ты классификатор обращений с лендинга разработчика.
Верни ТОЛЬКО JSON объект вида:
{"request_type":"<one of: lead, question, bug, partnership, other>","confidence":0.0}
Правила:
- lead: желание сотрудничать / заказ / коммерция
- question: общий вопрос
- bug: сообщение о проблеме / ошибке
- partnership: партнёрство / интеграция
- other: всё остальное
""".strip()

REPLY_PROMPT = """
Ты помощник владельца сайта-портфолио разработчика.
Напиши короткий вежливый ответ на русском (4-6 предложений) на обращение пользователя.
Не обещай сроков, которых нет. Не выдумывай контакты.
Верни ТОЛЬКО текст ответа без markdown.
""".strip()


@dataclass
class AIResult:
    available: bool
    request_type: str | None
    reply: str | None
    error: str | None = None


class AIService:
    VALID_TYPES = {"lead", "question", "bug", "partnership", "other"}

    def analyze(self, *, name: str, comment: str) -> AIResult:
        if not settings.OPENAI_API_KEY:
            return AIResult(
                available=False,
                request_type=None,
                reply=None,
                error="OPENAI_API_KEY is not configured",
            )

        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                timeout=settings.OPENAI_TIMEOUT_SECONDS,
            )
            request_type = self._classify(client, name=name, comment=comment)
            reply = self._generate_reply(client, name=name, comment=comment, request_type=request_type)
            return AIResult(
                available=True,
                request_type=request_type,
                reply=reply,
                error=None,
            )
        except Exception as exc:
            logger.exception("AI processing failed, using fallback")
            return AIResult(
                available=False,
                request_type=None,
                reply=None,
                error=str(exc),
            )

    def _classify(self, client, *, name: str, comment: str) -> str:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": CLASSIFY_PROMPT},
                {
                    "role": "user",
                    "content": f"Имя: {name}\nКомментарий: {comment}",
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        request_type = str(payload.get("request_type", "other")).lower().strip()
        if request_type not in self.VALID_TYPES:
            return "other"
        return request_type

    def _generate_reply(self, client, *, name: str, comment: str, request_type: str) -> str:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0.4,
            messages=[
                {"role": "system", "content": REPLY_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Имя: {name}\n"
                        f"Тип обращения: {request_type}\n"
                        f"Комментарий: {comment}"
                    ),
                },
            ],
        )
        return (response.choices[0].message.content or "").strip()

    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY)
