# Threat Model — DFD (Study Notes API)

## Контекст и границы доверия
- Client (Untrusted): браузер/пользователь
- Edge: публичный вход (reverse proxy / API gateway)
- Core: FastAPI (CRUD заметок/тегов), сервис логов/метрик
- Data: БД (notes, tags, note_tag), хранилище логов/метрик
- External (Future): внешний провайдер аутентификации

## DFD (Mermaid)

```mermaid
flowchart LR
  %% Внешние участники
  user[User / Browser]
  ext_idp[IdP / Auth Provider Future]
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
  subgraph TB_Core[Trust Boundary: Core App]
    app[FastAPI App<br/> Notes and Tags]
    logsvc[Logging / Observability<br/>PII masking, correlation id]
  end

  %% --- Trust Boundary: Data (Storage) ---
  subgraph TB_Data[Trust Boundary: Data]
    db[Relational DB<br/>tables: notes, tags, note_tag]
    logs[Logs / Metrics Storage]
  end

  %% --- External / Out of Control ---
  subgraph TB_External[External / Out of Control]
    ext_idp
    dev
  end

  %% --- Flows (F1..F12) ---
  %% Client -> Edge -> Core
  user -- "F1: HTTPS / GET /notes?limit=.." --> gw
  gw   -- "F2: HTTPS (mTLS internal) /notes,/tags" --> app

  %% Create / Update notes
  user -- "F3: HTTPS / POST /notes {title, body, tags[]}" --> gw
  gw   -- "F4: HTTPS (mTLS) POST /notes" --> app

  %% App <-> DB
  app  -- "F5: TCP driver CRUD notes/tags" --> db
  db   -- "F6: TCP driver rows/results" --> app

  %% App -> Logging
  app  -- "F7: async HTTP/UDP structured logs<br/>no PII, correlation id" --> logsvc
  logsvc -- "F8: batch HTTP persist logs/metrics" --> logs

  %% CI → App (supply chain)
  dev -- "F9: CI/CD push or PR<br/>SCA / SBOM reports" --> app

  %% (Future) Auth
  user -- "F10: HTTPS /auth/login" --> gw
  gw -- "F11: HTTPS (mTLS) /auth/login" --> app
  app -- "F12: HTTPS OIDC token/claims" --> ext_idp
````

### Список потоков (для связи со STRIDE/RISKS)

| ID  | Откуда → Куда               | Канал/протокол         | Данные / PII                            | Комментарий                             |
| --- | --------------------------- | ---------------------- | --------------------------------------- | --------------------------------------- |
| F1  | User → Gateway              | HTTPS                  | query, cookies                          | Публичный вход; нужна пагинация         |
| F2  | Gateway → App               | HTTPS (mTLS, внутр.)   | REST JSON                               | Внутренний защищённый канал             |
| F3  | User → Gateway              | HTTPS                  | note.title, **note.body**, tags[]       | Тело заметки потенциально чувствительно |
| F4  | Gateway → App               | HTTPS (mTLS)           | POST /notes JSON                        | Валидация схемы/лимитов на Edge/Core    |
| F5  | App → DB                    | TCP (DB driver)        | CRUD rows                               | Транзакции, инварианты Note↔Tags        |
| F6  | DB → App                    | TCP (DB driver)        | Rows                                    | Результаты запросов                     |
| F7  | App → Logging               | HTTP/UDP/Agent (async) | **без PII**, correlation id, метаданные | Маскирование PII, обязателен corr-id    |
| F8  | Logging → Logs Storage      | HTTP/Bulk              | Logs/metrics                            | Ретеншн/шардирование                    |
| F9  | Dev/CI → App                | Git/HTTPS, SBOM/SCA    | Манифесты завис.                        | Supply chain; отчёты в PR               |
| F10 | User → Gateway (future)     | HTTPS                  | creds                                   | Логин (будущее)                         |
| F11 | Gateway → App (future)      | HTTPS (mTLS)           | /auth/login                             | Прокси логина                           |
| F12 | App → External IdP (future) | HTTPS / OIDC           | tokens/claims                           | Внешний IdP                             |
