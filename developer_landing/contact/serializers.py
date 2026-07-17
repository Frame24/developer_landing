from __future__ import annotations

import re

from rest_framework import serializers


class ContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, trim_whitespace=True)
    phone = serializers.CharField(max_length=32, trim_whitespace=True)
    email = serializers.EmailField()
    comment = serializers.CharField(min_length=5, max_length=5000, trim_whitespace=True)

    PHONE_RE = re.compile(r"^\+?[0-9()\-\s]{7,32}$")

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Имя должно содержать минимум 2 символа.")
        if any(ch.isdigit() for ch in cleaned):
            raise serializers.ValidationError("Имя не должно содержать цифры.")
        return cleaned

    def validate_phone(self, value: str) -> str:
        cleaned = value.strip()
        if not self.PHONE_RE.match(cleaned):
            raise serializers.ValidationError(
                "Некорректный телефон. Используйте цифры, пробелы, +, -, ().",
            )
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 7:
            raise serializers.ValidationError("В телефоне слишком мало цифр.")
        return cleaned

    def validate_comment(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Комментарий обязателен.")
        return cleaned
