# ADR-005 — Safe HTTP Client for External Integrations

**Status:** Accepted
**Date:** 2025-11-09

## Context
Импорт тегов реализован через StackExchange API. Без таймаутов и ограничений возможно зависание или SSRF.

## Decision
Создан модуль `infrastructure/http_client.py` с классом `safe_http`, который:
- использует `httpx.AsyncClient` с `timeout=5s`;
- делает до 3 ретраев с экспоненциальной задержкой;
- проверяет хост по allow-list перед вызовом;
- возвращает JSON и выбрасывает `HTTPException(502)` при ошибках сети.

## Consequences
Все внешние вызовы проходят через один безопасный клиент.
