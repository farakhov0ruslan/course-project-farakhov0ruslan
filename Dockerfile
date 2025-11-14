#  builder
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# hadolint ignore=DL3008
# Не пиним версии системных пакетов, чтобы получать security-обновления.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt pyproject.toml ./

# hadolint ignore=DL3013
# Обновляем именно pip, поэтому не пиним его версию.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -requirement requirements.txt

#  runtime
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем только установленные зависимости из builder-образа
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# hadolint ignore=DL3008
# Не пиним версии системных пакетов, чтобы получать security-обновления.
RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*


# Создаём отдельного пользователя для приложения
RUN addgroup --system app \
    && adduser --system --ingroup app app

# Копируем код приложения (без тестов и мусора)
COPY app app
COPY core core
COPY infrastructure infrastructure
COPY utils_library utils_library
COPY pyproject.toml requirements*.txt ./

# Выдаём права пользователю app
RUN chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import http.client,sys; c=http.client.HTTPConnection('127.0.0.1',8000,timeout=2); \
c.request('GET','/health'); r=c.getresponse(); sys.exit(0 if r.status==200 else 1)" || exit 1

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
