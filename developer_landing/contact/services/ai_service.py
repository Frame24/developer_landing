from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger("developer_landing.contact")

CLASSIFY_PROMPT = """
Ты классификатор обращений с лендинга backend-разработчика.
Верни ТОЛЬКО JSON: {"request_type":"<тип>","confidence":0.0-1.0}

Выбери РОВНО один тип. Приоритет сверху вниз (если подходит несколько, бери верхний):

1) bug — баг, ошибка, падение, 500, не работает, сломалось, issue, crash
2) partnership — партнёрство, интеграция, API jointly, white-label, совместный продукт
3) lead — заказ, коммерция, разработка под ключ, нужен разработчик, коммерческое предложение, бюджет, ставка, вакансия/оффер работы
4) question — общий вопрос без заказа: как устроено, стек, опыт, можно ли созвониться уточнить
5) other — не подходит ни под что выше

Не угадывай. Если сомневаешься между lead и question: есть явный заказ/оплата/найм → lead, иначе question.
Не путай partnership и lead: partnership = совместная работа/интеграция продуктов; lead = клиент хочет нанять/заказать.
""".strip()

REPLY_PROMPT = """
Ты помощник владельца сайта-портфолио разработчика.
Напиши короткий вежливый ответ на русском (4-6 предложений) на обращение пользователя.
Не обещай сроков, которых нет. Не выдумывай контакты.
Верни ТОЛЬКО текст ответа без markdown.
""".strip()

# Deterministic rules first — openrouter/free switches models and is unstable.
_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "bug",
        (
            "баг",
            "ошибк",
            "не работает",
            "сломал",
            "падает",
            "crash",
            "bug",
            "issue",
            "500",
            "404",
            "traceback",
            "exception",
            "глючит",
            "лаг",
        ),
    ),
    (
        "partnership",
        (
            "партнёр",
            "партнер",
            "partnership",
            "интеграц",
            "совместн",
            "white-label",
            "whitelabel",
            "co-brand",
            "взаимодейств",
        ),
    ),
    (
        "lead",
        (
            "заказ",
            "нужен разработчик",
            "нужен backend",
            "коммерческ",
            "бюджет",
            "ставк",
            "оплат",
            "проект под ключ",
            "хочу заказать",
            "нанять",
            "ваканси",
            "оффер",
            "сотрудничеств",
            "аутсорс",
            "outsource",
            "hire",
            "commercial",
        ),
    ),
    (
        "question",
        (
            "вопрос",
            "подскаж",
            "расскаж",
            "как устроен",
            "какой стек",
            "можно ли",
            "интересно узнать",
            "уточн",
            "созвон",
            "созвониться",
            "?",
        ),
    ),
]


@dataclass
class AIResult:
    available: bool
    request_type: str | None
    reply: str | None
    error: str | None = None


class AIService:
    VALID_TYPES = {"lead", "question", "bug", "partnership", "other"}

    def analyze(self, *, name: str, comment: str) -> AIResult:
        # Classification is rule-first for stability; AI only for reply (and
        # optional classify fallback when rules say "other").
        request_type = self._classify_by_rules(comment)

        if not settings.OPENAI_API_KEY:
            return AIResult(
                available=False,
                request_type=request_type,
                reply=None,
                error="OPENAI_API_KEY is not configured",
            )

        try:
            from openai import OpenAI

            client_kwargs = {
                "api_key": settings.OPENAI_API_KEY,
                "timeout": settings.OPENAI_TIMEOUT_SECONDS,
            }
            if settings.OPENAI_BASE_URL:
                client_kwargs["base_url"] = settings.OPENAI_BASE_URL
            client = OpenAI(**client_kwargs)

            if request_type == "other":
                request_type = self._classify_with_ai(client, name=name, comment=comment)

            reply = self._generate_reply(
                client,
                name=name,
                comment=comment,
                request_type=request_type,
            )
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
                request_type=request_type,
                reply=None,
                error=str(exc),
            )

    def _classify_by_rules(self, comment: str) -> str:
        text = (comment or "").lower().replace("ё", "е")
        # Normalize punctuation-heavy typos a bit.
        text = re.sub(r"\s+", " ", text)
        for request_type, keywords in _RULES:
            for keyword in keywords:
                if keyword in text:
                    return request_type
        return "other"

    def _classify_with_ai(self, client, *, name: str, comment: str) -> str:
        messages = [
            {"role": "system", "content": CLASSIFY_PROMPT},
            {
                "role": "user",
                "content": f"Имя: {name}\nКомментарий: {comment}",
            },
        ]
        kwargs = {
            "model": settings.OPENAI_MODEL,
            "temperature": 0,
            "messages": messages,
        }
        try:
            response = client.chat.completions.create(
                **kwargs,
                response_format={"type": "json_object"},
            )
        except Exception:
            response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        payload = self._parse_json(content)
        request_type = str(payload.get("request_type", "other")).lower().strip()
        if request_type not in self.VALID_TYPES:
            return "other"
        return request_type

    @staticmethod
    def _parse_json(content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    return {}
            return {}

    def _generate_reply(self, client, *, name: str, comment: str, request_type: str) -> str:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
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
