import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


APP_NAME = "MahilMartLicenseManagerWeb"
APP_PORT = "8001"

_STDIO_STREAM = None


def _runtime_dir():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        root = Path(local_appdata)
    else:
        root = Path.home() / "AppData" / "Local"
    path = root / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _setup_logging():
    log_dir = _runtime_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "startup.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def _ensure_stdio():
    global _STDIO_STREAM
    if sys.stdout is not None and sys.stderr is not None:
        return

    log_dir = _runtime_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "startup.log"

    _STDIO_STREAM = open(log_file, "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _STDIO_STREAM
    if sys.stderr is None:
        sys.stderr = _STDIO_STREAM


def _load_env_file(path: Path):
    if not path.exists():
        return

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        logging.exception("Failed to read config file: %s", path)
        return

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            os.environ.setdefault(key, value)


def _prepare_runtime_environment():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "license_manager_web.settings")
    os.environ.setdefault("LICENSE_MANAGER_DEBUG", "1")

    config_candidates = []
    if getattr(sys, "frozen", False):
        config_candidates.append(Path(sys.executable).resolve().parent / "db_config.env")
    config_candidates.append(Path(__file__).resolve().parent / "db_config.env")
    config_candidates.append(_runtime_dir() / "db_config.env")

    for config_path in config_candidates:
        if config_path.exists():
            logging.info("Loading runtime config: %s", config_path)
            _load_env_file(config_path)
            break

    # Fallback for dev/test environments where PostgreSQL config is not provided.
    if not os.environ.get("MAHILMART_LICENSE_DB_NAME") and not os.environ.get("MAHILMART_LICENSE_DB_PATH"):
        db_dir = _runtime_dir()
        db_path = db_dir / "db.sqlite3"
        os.environ.setdefault("MAHILMART_LICENSE_DB_PATH", str(db_path))


def _merge_allowed_hosts(*hosts):
    merged = []
    seen = set()
    for host in hosts:
        value = (host or "").strip()
        if not value:
            continue
        for item in value.split(","):
            candidate = item.strip()
            if not candidate:
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(candidate)
    return ",".join(merged)


def _detect_machine_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if host_ip and not host_ip.startswith("127."):
            return host_ip
    except OSError:
        pass

    return ""


def _open_browser(app_url):
    time.sleep(1.5)
    webbrowser.open(app_url)


def _run_migrations_if_needed():
    from django.core.management import call_command
    from django.db import DEFAULT_DB_ALIAS, connections
    from django.db.migrations.executor import MigrationExecutor

    connection = connections[DEFAULT_DB_ALIAS]
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    if plan:
        logging.info("Pending migrations found. Running migrate.")
        call_command(
            "migrate",
            interactive=False,
            run_syncdb=True,
            verbosity=1,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    else:
        logging.info("No pending migrations.")


def main():
    _setup_logging()
    _ensure_stdio()
    _prepare_runtime_environment()

    from django import setup as django_setup
    from django.core.management import execute_from_command_line

    browser_host = _detect_machine_ip() or "127.0.0.1"
    preferred_open_host = (os.environ.get("LICENSE_MANAGER_BROWSER_HOST") or "ip").strip()
    preferred_open_host_lower = preferred_open_host.lower()
    if preferred_open_host_lower in {"", "ip"}:
        preferred_open_host = browser_host
    elif preferred_open_host_lower in {"local", "localhost"}:
        preferred_open_host = "127.0.0.1"

    os.environ["LICENSE_MANAGER_ALLOW_IP_MODE"] = "1"
    os.environ["LICENSE_MANAGER_ALLOWED_HOSTS"] = _merge_allowed_hosts(
        os.environ.get("LICENSE_MANAGER_ALLOWED_HOSTS", ""),
        preferred_open_host,
        browser_host,
        "127.0.0.1",
        "localhost",
    )

    django_setup()
    _run_migrations_if_needed()

    app_url = f"http://{preferred_open_host}:{APP_PORT}/"

    threading.Thread(target=_open_browser, args=(app_url,), daemon=True).start()
    execute_from_command_line(
        ["manage.py", "runserver", f"0.0.0.0:{APP_PORT}", "--noreload"]
    )


if __name__ == "__main__":
    main()
