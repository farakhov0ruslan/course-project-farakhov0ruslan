## ADR-001 — Problem Details (RFC 9457) + Correlation ID для ошибок API

**Status:** Accepted
**Date:** 2025-10-22
**Component:** FastAPI app (`app/main.py`), error handlers, middleware
**Related NFR:** NFR-01 (Ошибки в формате RFC7807/9457 + correlation_id)

### Context

Нужен единый предсказуемый формат ошибок и трассировка запросов. Стандарт **Problem Details** (RFC 9457) описывает машинно-читаемую форму ошибок и **обновляет/заменяет** RFC 7807. В каждой ошибке должен быть `correlation_id`, чтобы находить связанные логи/запросы. В FastAPI это реализуется через кастомные **exception handlers** и **ASGI-middleware** для request/correlation ID.
— RFC 9457 (обновляет RFC 7807). ([RFC Editor][1])
— FastAPI: кастомные exception-handlers. ([FastAPI][2])
— asgi-correlation-id: читает/генерирует `X-Request-ID`, можно настроить валидатор/генератор. ([GitHub][3])

### Decision

1. Включили **CorrelationIdMiddleware**:

   ```py
   app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")
   ```

   (по умолчанию принимает UUIDv4; при отсутствии — генерирует новый ID). ([PyPI][4])
2. Определили **единые обработчики**:

   * `@app.exception_handler(HTTPException)` → 4xx/5xx,
   * `@app.exception_handler(RequestValidationError)` → 422,
   * `@app.exception_handler(Exception)` → 500 (catch-all).
     Каждый возвращает JSON **Problem Details**: `type`, `title`, `status`, `detail`, `instance`, `correlation_id`. ([FastAPI][2])
3. Тесты: проверяем 404, 422 (валидация), 500, а также проброс/генерацию `correlation_id`. Для проверки 500 используем `TestClient(..., raise_server_exceptions=False)` (иначе Starlette пробрасывает исключение, а не ответ). ([starlette.dev][5])

### Consequences

**Плюсы**

* Единый envelope ошибок повышает DX, упрощает контракт-тесты и клиенты.
* `correlation_id` упрощает расследование инцидентов и трассировку в логах.
* Ошибки не «болтливы»: без стеков/секретов → меньше Info Disclosure.

**Минусы/риски**

* Нужно следить за консистентностью полей `detail/errors`.
* Клиенты должны учитывать формат Problem Details (но это стандарт де-факто).

### Security Impact

* Снижается риск **Information Disclosure** (STRIDE=I): ошибки стандартизованы, без лишних деталей (RFC 9457). ([RFC Editor][1])
* Улучшается **Repudiation/Аудит** (STRIDE=R): есть `correlation_id` во всех ошибках и логах (в связке с политикой логирования из NFR-03/OWASP Logging CS). ([cheatsheetseries.owasp.org][6])

### Implementation (ссылка на код)

Файл: `app/main.py` (фрагменты)

```py
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc): ...

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc): ...

@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc): ...
```

### Testing / Evidence

Файл: `tests/test_problem_details.py`
Покрытие:

* **404**: ответ в формате Problem Details, `status=404`, `correlation_id` = входной `X-Request-ID` (UUIDv4).
* **422** (`/tags?limit=5000`): Problem Details + массив `errors`, `correlation_id` совпадает с заголовком.
* **500**: временный `/boom` генерирует исключение; с `TestClient(app, raise_server_exceptions=False)` получаем **JSON** Problem Details `status=500` и корректный `correlation_id`. ([starlette.dev][5])
* **Без заголовка**: библиотека генерирует валидный ID, поле `correlation_id` непустое. ([PyPI][4])

### Rollout / Ops

* Включено глобально в одном месте (минимальный риск).
* При смене требований к ID: настроить `validator=None` для произвольных ID или собственный валидатор/генератор. ([pydigger.com][7])
* Добавить в логи обязательное поле `correlation_id` (будет оформлено отдельным ADR для PII-safe logging, NFR-03). ([cheatsheetseries.owasp.org][6])

### Alternatives

* Возврат произвольных JSON-ошибок → нет стандарта, сложнее поддерживать клиентов.
* 7807 вместо 9457 → формально устаревшая редакция (9457 «obsoletes 7807»). ([RFC Editor][1])

### Traceability

* **NFR:** NFR-01 (ошибки в формате RFC7807/9457 + correlation_id).
* **DFD/Flows:** F1/F3/F7 — точки, где чаще всего возникают 4xx/5xx и валидация.
* **STRIDE:** I, R на публичных/валидационных путях.
* **RISKS:** R-05, R-09 — «непредсказуемые/болтливые ошибки» → mitigated.

### Acceptance Criteria (проверка)

* ✅ Все 404/422/500 возвращают JSON Problem Details (RFC 9457).
* ✅ В каждом ответе есть `correlation_id` (совпадает с валидным UUID из заголовка).
* ✅ Тест 500 использует `raise_server_exceptions=False` и получает корректный body. ([starlette.dev][5])
* ✅ Контракт-тесты зелёные в CI.

### References

* RFC 9457 — *Problem Details for HTTP APIs* (obsoletes 7807).
* FastAPI — *Handling Errors* (кастомные exception-handlers).
* Starlette — *TestClient* (флаг `raise_server_exceptions`).
* asgi-correlation-id — docs/README и параметры middleware.
* OWASP Logging Cheat Sheet / A09:2021 (контекст для логирования и корреляции).
