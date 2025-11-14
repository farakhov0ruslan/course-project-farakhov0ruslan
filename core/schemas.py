from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TagCreate(BaseModel):
    """Создание тега с нормализацией имени"""

    name: str = Field(..., min_length=1, max_length=32, description="Имя тега")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Нормализация: strip + lowercase + запрет спецсимволов"""
        normalized = v.strip().lower()
        if not normalized:
            raise ValueError("Tag name cannot be empty after normalization")
        if not normalized.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Tag name must contain only alphanumeric characters, hyphens, or underscores"
            )
        return normalized

    model_config = ConfigDict(str_strip_whitespace=True)


class TagRead(BaseModel):
    """Чтение тега"""

    id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=32)

    model_config = ConfigDict(from_attributes=True)


class NoteCreate(BaseModel):
    """Создание заметки с валидацией всех полей"""

    title: str = Field(
        ..., min_length=1, max_length=200, description="Заголовок заметки"
    )
    body: str = Field(default="", max_length=10000, description="Содержимое заметки")
    tags: List[str] = Field(
        default_factory=list, max_length=20, description="Список тегов"
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Trim whitespace и проверка на пустоту"""
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty or contain only whitespace")
        return v

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        """Нормализация body (опционально)"""
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Нормализация тегов: strip + lowercase + уникальность"""
        if not v:
            return []
        normalized = [tag.strip().lower() for tag in v if tag.strip()]
        # Проверка уникальности
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate tags are not allowed")
        # Проверка длины каждого тега
        for tag in normalized:
            if len(tag) > 32:
                raise ValueError(f"Tag '{tag}' exceeds maximum length of 32 characters")
            if not tag.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"Tag '{tag}' contains invalid characters")
        return normalized

    model_config = ConfigDict(str_strip_whitespace=True)


class NoteUpdate(BaseModel):
    """Обновление заметки — все поля Optional"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    body: Optional[str] = Field(None, max_length=10000)
    tags: Optional[List[str]] = Field(None, max_length=20)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty or contain only whitespace")
        return v

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        normalized = [tag.strip().lower() for tag in v if tag.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate tags are not allowed")
        for tag in normalized:
            if len(tag) > 32:
                raise ValueError(f"Tag '{tag}' exceeds maximum length of 32 characters")
            if not tag.replace("-", "").replace("_", "").isalnum():
                raise ValueError(f"Tag '{tag}' contains invalid characters")
        return normalized

    model_config = ConfigDict(str_strip_whitespace=True)


class NoteRead(BaseModel):
    """Чтение заметки"""

    id: int = Field(..., gt=0)
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(default="", max_length=10000)
    tags: List[TagRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ImportStats(BaseModel):
    total_rows: int = Field(..., description="Всего строк в файле")
    imported: int = Field(..., description="Успешно импортировано")
    skipped: int = Field(..., description="Пропущено (ошибки валидации)")
    errors: List[str] = Field(default_factory=list, description="Список ошибок")


class ImportResponse(BaseModel):
    status: Literal["success", "partial", "failed"]
    stats: ImportStats
    message: str
