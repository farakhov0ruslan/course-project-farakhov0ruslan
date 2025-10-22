import re

from utils_library.logger import get_logger


def test_masks_pii_fields(log_capture):
    log = get_logger("test.pii")
    # поля из denylist должны быть замаскированы твоим форматтером
    log.info("note.payload", body="SECRET", password="p@ss", token="abc")
    rec = log_capture()
    assert rec["message"] == "note.payload"
    assert rec.get("body") == "***"
    assert rec.get("password") == "***"
    assert rec.get("token") == "***"


def test_sanitizes_reserved_keys_without_crash(log_capture):
    log = get_logger("test.reserved")
    # 'name' зарезервирован для LogRecord → наша обёртка должна переименовать (например, field_name)
    log.info("tag.not_found", name="temp")
    rec = log_capture()
    # системное имя логгера остаётся корректным
    assert rec.get("logger") == "test.reserved"
    # значение из extra попало в безопасное поле
    assert rec.get("field_name") == "temp"


def test_outputs_valid_json_shape(log_capture):
    log = get_logger("test.json")
    log.warning("notes.listed", count=2, limit=50, offset=0)
    rec = log_capture()
    # базовые поля нашего JSON-формата
    assert set(["ts", "level", "logger", "message"]).issubset(rec.keys())
    assert rec["logger"] == "test.json"
    assert rec["level"] in ("INFO", "WARNING", "ERROR", "DEBUG")
    # пользовательские поля присутствуют
    assert rec.get("count") == 2
    # ts похож на ISO-строку с миллисекундами
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", rec["ts"])
