import configparser
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from django.conf import settings

from .models import LicenseRuntimeConfig


def normalize_machine_id(machine_id):
    value = (machine_id or "").strip().upper()
    value = re.sub(r"\s+", "", value)
    return value


def is_machine_id_valid(machine_id):
    value = normalize_machine_id(machine_id)
    return bool(re.fullmatch(r"[A-Z0-9._-]{3,64}", value))


def is_browser_style_machine_id(machine_id):
    value = normalize_machine_id(machine_id)
    return bool(
        re.fullmatch(
            r"POS-[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}",
            value,
        )
    )


def _build_checksum_value(seed, multiplier, offset):
    total = 0
    modulus = 16777215
    for index, char in enumerate(seed, start=1):
        total = (total + (ord(char) + offset) * (index + multiplier)) % modulus
    return total


def _generate_modern_license_key(seed):
    uppercase_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lowercase_chars = "abcdefghijkmnopqrstuvwxyz"
    number_chars = "23456789"
    special_chars = "@#$%&*!?"
    modulus = 16777215

    state = (
        _build_checksum_value(seed, 3, 11)
        + _build_checksum_value(seed, 7, 19)
        + len(seed) * 97
    ) % modulus

    base_chars = []
    for index in range(30):
        state = (state * 73 + 19 + index * 131) % modulus
        if index % 3 == 0:
            charset = uppercase_chars
        elif index % 3 == 1:
            charset = lowercase_chars
        else:
            charset = number_chars
        base_chars.append(charset[state % len(charset)])

    base_key = "".join(base_chars)
    state = (state * 73 + 17) % modulus
    special_a = special_chars[state % len(special_chars)]
    state = (state * 73 + 29) % modulus
    special_b = special_chars[state % len(special_chars)]
    return f"{base_key[:10]}{special_a}{base_key[10:20]}{special_b}{base_key[20:]}"


def _normalize_generation_time(generated_at=None):
    value = generated_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _license_key_window_start(generated_at=None):
    window_minutes = get_license_key_validity_minutes()
    window_seconds = window_minutes * 60
    generated_at_utc = _normalize_generation_time(generated_at)
    bucket_index = int(generated_at_utc.timestamp()) // window_seconds
    return datetime.fromtimestamp(bucket_index * window_seconds, tz=timezone.utc)


def _license_key_seed_mode():
    return (getattr(settings, "LICENSE_KEY_SEED_MODE", "windowed") or "windowed").strip().lower()


def generate_machine_license_key(machine_id, generated_at=None):
    machine = normalize_machine_id(machine_id)
    if _license_key_seed_mode() == "pos_static":
        seed = f"{settings.LICENSE_EMAIL.upper()}|{machine}"
    else:
        window_start = _license_key_window_start(generated_at)
        seed = f"{settings.LICENSE_EMAIL.upper()}|{machine}|{window_start.strftime('%Y%m%d%H%M')}"
    return _generate_modern_license_key(seed)


def get_license_key_validity_minutes():
    raw_value = getattr(settings, "LICENSE_KEY_VALIDITY_MINUTES", 10)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = 10
    return max(1, value)


def calculate_license_valid_until(generated_at=None):
    value = generated_at or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value + timedelta(minutes=get_license_key_validity_minutes())


def _shared_mongo_config_path():
    custom_path = (os.environ.get("MAHILMARTPOS_SHARED_MONGO_CONFIG_PATH") or "").strip()
    if custom_path:
        return Path(custom_path)
    return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "MahilMartPOS" / "license_mongo_config.ini"


def read_shared_mongo_config():
    config_path = _shared_mongo_config_path()
    if not config_path.exists():
        return {}

    parser = configparser.ConfigParser(interpolation=None)
    try:
        parser.read(config_path, encoding="utf-8")
    except Exception:
        return {}

    if "mongo" not in parser:
        return {}

    section = parser["mongo"]
    return {
        "mongo_uri": (section.get("mongo_uri") or "").strip(),
        "mongo_db": (section.get("mongo_db") or "").strip(),
        "mongo_collection": (section.get("mongo_collection") or "").strip(),
    }


def save_shared_mongo_config(*, mongo_uri, mongo_db, mongo_collection):
    config_path = _shared_mongo_config_path()
    parser = configparser.ConfigParser(interpolation=None)
    parser["mongo"] = {
        "mongo_uri": (mongo_uri or "").strip(),
        "mongo_db": (mongo_db or "").strip(),
        "mongo_collection": (mongo_collection or "").strip(),
    }

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file_obj:
            parser.write(file_obj)
        return True, f"POS shared Mongo config updated: {config_path}"
    except Exception as exc:
        return False, f"Could not update POS shared Mongo config: {exc}"


def get_runtime_mongo_config():
    mongo_uri = (settings.LICENSE_MONGO_URI or "").strip()
    mongo_db = (settings.LICENSE_MONGO_DB or "").strip()
    mongo_collection = (settings.LICENSE_MONGO_COLLECTION or "").strip()
    shared_config = read_shared_mongo_config()

    if shared_config:
        mongo_uri = shared_config.get("mongo_uri") or mongo_uri
        mongo_db = shared_config.get("mongo_db") or mongo_db
        mongo_collection = shared_config.get("mongo_collection") or mongo_collection

    try:
        runtime_config = LicenseRuntimeConfig.get_singleton()
    except Exception:
        runtime_config = None

    if runtime_config is None:
        return {
            "mongo_uri": mongo_uri,
            "mongo_db": mongo_db,
            "mongo_collection": mongo_collection,
        }

    return {
        "mongo_uri": (runtime_config.mongo_uri or mongo_uri).strip(),
        "mongo_db": (runtime_config.mongo_db or mongo_db).strip(),
        "mongo_collection": (runtime_config.mongo_collection or mongo_collection).strip(),
    }


def sync_to_mongo(payload):
    runtime_mongo = get_runtime_mongo_config()
    mongo_uri = runtime_mongo["mongo_uri"]
    if not mongo_uri:
        return False, "Mongo URI empty. Saved only in local Django database."

    try:
        from pymongo import MongoClient
    except Exception:
        return False, "pymongo package not installed. Saved only in local Django database."

    now_utc = datetime.now(timezone.utc)
    generated_at = payload.get("generated_at") or now_utc
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    valid_until = payload.get("valid_until") or calculate_license_valid_until(generated_at)
    if valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=timezone.utc)

    document = {
        "license_key": payload["license_key"],
        "machine_id": payload["machine_id"],
        "license_email": settings.LICENSE_EMAIL,
        "customer_name": payload.get("customer_name", ""),
        "contact_email": payload.get("contact_email", ""),
        "note": payload.get("note", ""),
        "generated_by": payload.get("generated_by", ""),
        "generated_at": generated_at,
        "valid_until": valid_until,
        "status": payload.get("status", "valid"),
        "source": payload.get("source", getattr(settings, "LICENSE_SOURCE", "license_manager_page")),
    }

    client = None
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        collection = client[runtime_mongo["mongo_db"]][runtime_mongo["mongo_collection"]]
        collection.update_one(
            {"machine_id": document["machine_id"]},
            {
                "$set": document,
                "$setOnInsert": {
                    "created_at": now_utc,
                },
            },
            upsert=True,
        )
        collection.delete_many(
            {
                "machine_id": document["machine_id"],
                "license_key": {"$ne": document["license_key"]},
            }
        )
        return True, "Saved to MongoDB."
    except Exception as exc:
        return False, f"Mongo sync failed: {exc}"
    finally:
        if client is not None:
            client.close()


def fetch_recent_mongo_licenses(limit=100):
    runtime_mongo = get_runtime_mongo_config()
    mongo_uri = runtime_mongo["mongo_uri"]
    if not mongo_uri:
        return []

    try:
        from pymongo import DESCENDING, MongoClient
    except Exception:
        return []

    client = None
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        collection = client[runtime_mongo["mongo_db"]][runtime_mongo["mongo_collection"]]
        cursor = collection.find({}, {"_id": 0}).sort("generated_at", DESCENDING).limit(max(limit, 1))

        documents = []
        for item in cursor:
            generated_at = item.get("generated_at")
            valid_until = item.get("valid_until")
            created_at = item.get("created_at")
            if generated_at is not None and generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=timezone.utc)
            if valid_until is None and generated_at is not None:
                valid_until = calculate_license_valid_until(generated_at)
            if valid_until is not None and valid_until.tzinfo is None:
                valid_until = valid_until.replace(tzinfo=timezone.utc)
            if created_at is not None and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            documents.append(
                {
                    "license_key": item.get("license_key", ""),
                    "machine_id": item.get("machine_id", ""),
                    "license_email": item.get("license_email", settings.LICENSE_EMAIL),
                    "customer_name": item.get("customer_name", ""),
                    "contact_email": item.get("contact_email", ""),
                    "note": item.get("note", ""),
                    "generated_by": item.get("generated_by", ""),
                    "generated_at": generated_at,
                    "valid_until": valid_until,
                    "created_at": created_at,
                    "status": item.get("status", "generated"),
                    "source": item.get("source", getattr(settings, "LICENSE_SOURCE", "license_manager_page")),
                }
            )

        return documents
    except Exception:
        return []
    finally:
        if client is not None:
            client.close()
