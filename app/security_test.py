"""
ТЕСТОВЫЙ ФАЙЛ ДЛЯ ПРОВЕРКИ SAST & SECRETS SCANNING
Этот файл содержит намеренные уязвимости для проверки pipeline.
УДАЛИТЬ ПОСЛЕ ПРОВЕРКИ!
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine

app = FastAPI()

# ❌ УЯЗВИМОСТЬ 1: Hardcoded API key (должен найти Gitleaks + Semgrep)
API_KEY = "sk_live_1234567890abcdefghijklmnopqrstuvwxyz"
SECRET_TOKEN = "super_secret_token_12345678"
DATABASE_PASSWORD = "MySecretP@ssw0rd123!"


# ❌ УЯЗВИМОСТЬ 2: SQL Injection (должен найти Semgrep)
def get_user_by_name(name: str, session):
    # Опасно: использование f-string в SQL
    query = f"SELECT * FROM users WHERE name = '{name}'"
    return session.execute(query).fetchall()


def search_users(search_term: str, session):
    # Опасно: конкатенация строк в SQL
    query = "SELECT * FROM users WHERE name LIKE '%" + search_term + "%'"
    return session.execute(query).fetchall()


# ❌ УЯЗВИМОСТЬ 3: XSS через HTMLResponse (должен найти Semgrep)
@app.get("/unsafe_hello")
def unsafe_hello(name: str):
    # Опасно: пользовательский ввод напрямую в HTML
    return HTMLResponse(f"<h1>Hello, {name}!</h1>")


@app.get("/unsafe_profile")
def unsafe_profile(user_input: str):
    # Опасно: XSS уязвимость
    html_content = f"""
    <html>
        <body>
            <p>User data: {user_input}</p>
        </body>
    </html>
    """
    return HTMLResponse(html_content)


# ❌ УЯЗВИМОСТЬ 4: Более хардкоженных секретов
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
STRIPE_API_KEY = "sk_test_4eC39HqLyjWDarjtT1zdp7dc"

# Database connection with hardcoded password
db_connection_string = "postgresql://admin:VerySecurePassword123@localhost/mydb"
engine = create_engine(db_connection_string)

# More secrets in different formats
config = {
    "api_key": "1234567890abcdef",
    "secret": "my-secret-token-999",
    "password": "AnotherHardcodedPass123",
}
