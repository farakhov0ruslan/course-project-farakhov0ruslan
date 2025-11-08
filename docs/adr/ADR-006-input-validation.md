# ADR-006 — Strict Input Validation and Normalization

**Status:** Accepted
**Date:** 2025-11-09

## Context
Импорт и CRUD-операции обрабатывают пользовательские данные, потенциально содержащие SQL-инъекции или невалидные поля.

## Decision
- Все схемы реализованы через `pydantic.BaseModel` в `core/schemas.py`;
- включён `model_config = {"extra": "forbid"}` — запрет неизвестных полей;
- поля `title`, `body` ограничены по длине;
- даты нормализуются в UTC;
- тесты проверяют длинные строки и неверные типы.

## Consequences
Минимизируется риск SQL-инъекций и утечек через плохо нормализованные поля.
