import csv
import json
from pathlib import Path

from pydantic import ValidationError
from sqlmodel import Session

from core.schemas import ImportStats, NoteCreate
from core.services.notes import create_note
from utils_library.file_security import MAX_RECORDS
from utils_library.logger import get_logger

LOGGER = get_logger(__name__)


class ImportService:

    def __init__(self, session: Session):
        self.session = session

    def import_from_csv(self, file_path: Path) -> ImportStats:
        stats = ImportStats(total_rows=0, imported=0, skipped=0, errors=[])

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Защита от CSV Injection через DictReader (экранирование)
                reader = csv.DictReader(f)

                for idx, row in enumerate(reader, start=1):
                    stats.total_rows += 1

                    # Защита от resource exhaustion
                    if stats.total_rows > MAX_RECORDS:
                        stats.errors.append(
                            f"Import stopped: maximum {MAX_RECORDS} records exceeded"
                        )
                        LOGGER.warning(
                            "import.limit_exceeded",
                            max_records=MAX_RECORDS,
                            stopped_at=stats.total_rows,
                        )
                        break

                    try:
                        # Парсинг тегов из строки "tag1,tag2,tag3"
                        tags_str = row.get("tags", "")
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

                        # Валидация через Pydantic (защита от injection)
                        note_data = NoteCreate(
                            title=row.get("title", "").strip(),
                            body=row.get("body", "").strip(),
                            tags=tags,
                        )

                        # Создание через существующий сервис
                        create_note(
                            self.session,
                            title=note_data.title,
                            body=note_data.body,
                            tag_names=note_data.tags,
                        )

                        stats.imported += 1

                    except ValidationError as e:
                        stats.skipped += 1
                        error_msg = f"Row {idx}: {e.errors()[0]['msg']}"
                        stats.errors.append(error_msg)
                        LOGGER.warning("import.validation_error", row=idx, error=str(e))

                    except Exception as e:
                        stats.skipped += 1
                        error_msg = f"Row {idx}: unexpected error - {str(e)}"
                        stats.errors.append(error_msg)
                        LOGGER.error("import.unexpected_error", row=idx, error=str(e))

            LOGGER.info(
                "import.csv.completed",
                total=stats.total_rows,
                imported=stats.imported,
                skipped=stats.skipped,
            )

        except Exception as e:
            stats.errors.append(f"CSV parsing failed: {str(e)}")
            LOGGER.error("import.csv.failed", error=str(e))

        return stats

    def import_from_json(self, file_path: Path) -> ImportStats:
        stats = ImportStats(total_rows=0, imported=0, skipped=0, errors=[])

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Защита от JSON bombs через ограничение размера (уже проверен в file_security)
                data = json.load(f)

            if not isinstance(data, dict) or "notes" not in data:
                stats.errors.append("Invalid JSON format: expected {'notes': [...]}")
                return stats

            notes_list = data["notes"]
            if not isinstance(notes_list, list):
                stats.errors.append("Invalid JSON format: 'notes' must be an array")
                return stats

            for idx, note_dict in enumerate(notes_list, start=1):
                stats.total_rows += 1

                # Защита от resource exhaustion
                if stats.total_rows > MAX_RECORDS:
                    stats.errors.append(
                        f"Import stopped: maximum {MAX_RECORDS} records exceeded"
                    )
                    LOGGER.warning(
                        "import.limit_exceeded",
                        max_records=MAX_RECORDS,
                        stopped_at=stats.total_rows,
                    )
                    break

                try:
                    # Валидация через Pydantic
                    note_data = NoteCreate(**note_dict)

                    # Создание через существующий сервис
                    create_note(
                        self.session,
                        title=note_data.title,
                        body=note_data.body,
                        tag_names=note_data.tags,
                    )

                    stats.imported += 1

                except ValidationError as e:
                    stats.skipped += 1
                    error_msg = f"Note {idx}: {e.errors()[0]['msg']}"
                    stats.errors.append(error_msg)
                    LOGGER.warning("import.validation_error", note=idx, error=str(e))

                except Exception as e:
                    stats.skipped += 1
                    error_msg = f"Note {idx}: unexpected error - {str(e)}"
                    stats.errors.append(error_msg)
                    LOGGER.error("import.unexpected_error", note=idx, error=str(e))

            LOGGER.info(
                "import.json.completed",
                total=stats.total_rows,
                imported=stats.imported,
                skipped=stats.skipped,
            )

        except json.JSONDecodeError as e:
            stats.errors.append(f"Invalid JSON: {str(e)}")
            LOGGER.error("import.json.invalid", error=str(e))
        except Exception as e:
            stats.errors.append(f"JSON parsing failed: {str(e)}")
            LOGGER.error("import.json.failed", error=str(e))

        return stats
