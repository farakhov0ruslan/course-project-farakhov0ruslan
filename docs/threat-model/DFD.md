# Threat Model — DFD (Study Notes API)

## Контекст и границы доверия
- **Client (Untrusted):** браузер/пользователь.
- **Edge:** публичный вход (Reverse-proxy/API gateway).
- **Core:** приложение FastAPI (CRUD заметок/тегов), сервис логов/метрик.
- **Data:** БД (notes, tags, note_tag), хранилище логов/метрик.
- (Future) **Auth/IdP:** внешний провайдер аутентификации.

> Примечание. Trust boundaries показывают зоны с разным уровнем контроля/доверия; это базовый элемент DFD в моделировании угроз. Источник: OWASP и Microsoft SDL.

## DFD (Mermaid)

```mermaid
flowchart LR
  %% Внешние участники
  user[User / Browser]
  ext_idp[(IdP / Auth Provider)\n(Future)]
  dev[Dev / CI Runner]

  %% --- Trust Boundary: Client (Untrusted) ---
  subgraph TB_Client[Trust Boundary: Client / Untrusted]
    user
  end

  %% --- Trust Boundary: Edge ---
  subgraph TB_Edge[Trust Boundary: Edge]
    gw[API Gateway / Reverse Proxy]
  end

  %% --- Trust Boundary: Core (App/Services) ---
  subgraph TB_Core[Trust Boundary: Core (App)]
    app[FastAPI App\n(Notes/Tags)]
    logsvc[Logging/Observability\n(PII-masking, corr-id)]
  end

  %% --- Trust Boundary: Data (Storage) ---
  subgraph TB_Data[Trust Boundary: Data]
    db[(Relational DB\nnotes, tags, note_tag)]
    logs[(Logs/Metrics Storage)]
  end

  %% --- External / Out of Control ---
  subgraph TB_External[External / Out of Control]
    ext_idp
    dev
  end

  %% --- Flows (нумерация F1..Fn) ---
  %% Client -> Edge -> Core
  user -- "F1: HTTPS / GET /notes?limit=.." --> gw
  gw   -- "F2: HTTPS (mTLS)\n/notes,/tags" --> app

  %% Create/Update notes
  user -- "F3: HTTPS / POST /notes {title, body, tags[]}" --> gw
  gw   -- "F4: HTTPS (mTLS)\nPOST /notes" --> app

  %% App <-> DB
  app  -- "F5: TCP (DB driver)\nCRUD notes/tags" --> db
  db   -- "F6: TCP (DB driver)\nRows/Results" --> app

  %% App -> Logging
  app  -- "F7: Async HTTP/UDP\nstructured logs (no PII), corr-id" --> logsvc
  logsvc -- "F8: Batch/HTTP\npersist logs/metrics" --> logs

  %% CI → App (supply-chain)
  dev -- "F9: CI/CD push/PR\nSCA/SBOM reports" --> app

  %% (Future) Auth
  user -- "F10: HTTPS /auth/login" --> gw
  gw -- "F11: HTTPS (mTLS)\n/auth/login" --> app
  app -- "F12: HTTPS / OIDC\nToken/claims" --> ext_idp
````

### Список потоков (для связи со STRIDE/RISKS)

| ID  | Откуда → Куда               | Канал/протокол         | Данные / PII                            | Комментарий                             |
| --- | --------------------------- | ---------------------- | --------------------------------------- | --------------------------------------- |
| F1  | User → Gateway              | HTTPS                  | query, cookies                          | Публичный вход; обязательна пагинация   |
| F2  | Gateway → App               | HTTPS (mTLS, внутр.)   | REST JSON                               | Edge→Core, защищённый внутренний канал  |
| F3  | User → Gateway              | HTTPS                  | **note.body**, title, tags[] (чувств.)  | Тело заметки потенциально чувствительно |
| F4  | Gateway → App               | HTTPS (mTLS)           | POST /notes JSON                        | Валидация схемы/лимитов на Edge/Core    |
| F5  | App → DB                    | TCP (driver)           | CRUD rows                               | Транзакции, инварианты Note↔Tags        |
| F6  | DB → App                    | TCP (driver)           | Rows                                    | Результаты запросов                     |
| F7  | App → Logging/Observability | HTTP/UDP/Agent (async) | **без PII**, correlation-id, метаданные | Маскирование PII, обязательный corr-id  |
| F8  | Logging → Logs Storage      | HTTP/Bulk              | Logs/metrics                            | Ретеншн/шардирование                    |
| F9  | Dev/CI → App                | Git/HTTPS, SBOM/SCA    | Манифесты зависимостей                  | Supply-chain; отчёты в PR               |
| F10 | User → Gateway (future)     | HTTPS                  | creds                                   | Логин (будущее)                         |
| F11 | Gateway → App (future)      | HTTPS (mTLS)           | /auth/login                             | Прокси логина                           |
| F12 | App → External IdP (future) | HTTPS / OIDC           | tokens/claims                           | Внешний IdP                             |

---

## Альтернативный сценарий (допустима 1 доп. диаграмма)

**Degraded logging:** временно нет связи с хранилищем логов — агент буферизует и ретраит.

```mermaid
flowchart LR
  subgraph TB_Core[Trust Boundary: Core]
    app[FastAPI App]
    logsvc[Logging Agent (buffer)]
  end
  subgraph TB_Data[Trust Boundary: Data]
    logs[(Logs Storage)]
  end

  app -- "F7a: structured logs (no PII), corr-id" --> logsvc
  logsvc -. "канал недоступен" .-> logs
  logsvc -- "F8a: bulk retry\nэкспоненциальная задержка" --> logs
```
