# NFR BDD — Study Notes API
# Сценарии привязаны к ID из NFR.md через теги @NFR-XX.
# Везде есть измеримые пороги в шагах Then.

@NFR-01
Feature: Единый формат ошибок (RFC7807 + correlation_id)
  Background:
    Given запущен сервис на stage
  Scenario: 404 на несуществующую заметку возвращается в RFC7807 c correlation_id
    When клиент делает GET /notes/999999
    Then статус ответа равен 404
    And тело ответа соответствует RFC7807 (application/problem+json)
    And поле "correlation_id" присутствует и непустое
    And тело ошибки не содержит PII (например, текста заметки)

@NFR-03
Feature: Политика логирования (без PII + request/correlation-id)
  Background:
    Given включено логирование запросов и ответов с редактированием чувствительных данных
  Scenario: Логи не содержат PII, каждый запрос трассируется
    When клиент выполняет POST /notes с телом длиной > 1000 символов и тегами ["math","analysis"]
    Then в логах присутствует request-id или correlation-id для запроса
    And в логах отсутствует содержимое поля "body" заметки в открытом виде
    And линтер логов возвращает 0 находок по шаблонам запрещённого содержимого

@NFR-07
Feature: Квоты и пагинация ответов
  Background:
    Given сервис развернут на stage
  Scenario: Ограничение limit применяется и валидируется
    When клиент делает GET /notes?limit=5000
    Then статус 400 или 422
    And тело ответа соответствует RFC7807
  Scenario: Значение limit по умолчанию
    When клиент делает GET /notes без параметров
    Then возвращается не более 50 элементов

@NFR-12
Feature: Производительность чтения заметок (GET /notes)
  Background:
    Given база содержит не менее 1000 заметок
    And сервис развернут на stage
  Scenario: p95 времени ответа при 100 RPS не хуже порога
    When запускается 5-минутный нагрузочный профиль GET /notes?limit=50 с интенсивностью 100 RPS
    Then рассчитанный p95 времени ответа ≤ 200 ms
    And процент ошибок (5xx) < 0.5%

@NFR-04
Feature: Целостность связей Note↔Tags
  Background:
    Given существует заметка id=NOTE1 с тегами ["math","algebra"]
    And существуют теги "math","algebra","analysis"
  Scenario: Обновление заметки атомарно меняет список тегов
    When клиент выполняет PATCH /notes/NOTE1 с телом { "tags": ["math","analysis"] }
    Then GET /notes/NOTE1 возвращает ровно теги ["math","analysis"]
    And в репозитории связей нет «висячих» ссылок на "algebra" для NOTE1
  Scenario: Массовые операции не нарушают инварианты
    When запускается property/fuzz тест из 10_000 случайных операций создания/обновления заметок и тегов
    Then количество несогласованностей связей равно 0

@NFR-05
Feature: Управление зависимостями (SCA/SBOM)
  Background:
    Given настроен SCA-сканер в CI для каждого push/PR
  Scenario: Высокие уязвимости обрабатываются в срок
    When появляется отчёт SCA с уязвимостью уровня High или Critical
    Then в трекере создаётся Issue в течение ≤ 3 дней (Triage ≤ 3 дня)
    And фикс уязвимости уровня High/Critical попадает в main в течение ≤ 7 дней с момента Triage

@NFR-06
Feature: Миграции и схема БД (идемпотентность и контроль)
  Background:
    Given все изменения схемы оформляются миграциями
  Scenario: Dry-run миграций успешен в CI
    When запускается пайплайн CI на pull request
    Then шаг "migrations dry-run" завершается успешно
    And повторный прогон миграций не изменяет схему (изменений 0)

# --- НИЖЕ СЦЕНАРИИ ДЛЯ «БУДУЩИХ» NFR ---

@future @NFR-02
Feature: Защита от перебора логина
  Background:
    Given включён rate limit для аутентификации
  Scenario: Блокировка при превышении лимита
    When с одного аккаунта и одного IP выполняется 6 попыток логина за минуту с неверным паролем
    Then на 6-й попытке сервер отвечает 429 Too Many Requests
    And в логах фиксируется событие "security.rate_limit"

@future @NFR-08
Feature: Токены доступа — TTL и аудит выпуска
  Background:
    Given сервис авторизации выпускает токены
  Scenario: Выдача токена соответствует TTL и пишется в аудит
    When пользователь успешно проходит логин
    Then выданный токен имеет TTL ≤ 60 минут
    And событие выпуска токена зафиксировано в аудит-логе

@future @NFR-10
Feature: Хранение паролей (Argon2id)
  Background:
    Given в конфигурации задан Argon2id (t=3, m=256MB, p=1)
  Scenario: Создание/смена пароля использует Argon2id с заданными параметрами
    When пользователь устанавливает или меняет пароль
    Then хэш пароля хранится в базе в формате Argon2id с параметрами t=3, m=256MB, p=1

@future @NFR-11
Feature: Производительность логина (POST /auth/login)
  Background:
    Given сервис авторизации развернут на stage
  Scenario: p95 логина при 50 RPS не хуже порога
    When запускается 5-минутный профиль POST /auth/login при 50 RPS с валидными учётными данными
    Then p95 времени ответа ≤ 300 ms
    And процент ошибок (5xx) < 1%
