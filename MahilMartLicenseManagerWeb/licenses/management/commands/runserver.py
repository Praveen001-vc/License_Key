import os

from django.core.management.base import CommandError
from django.core.management.commands.runserver import Command as DjangoRunserverCommand


class Command(DjangoRunserverCommand):
    default_addr = "127.0.0.1"
    default_port = "8001"
    _local_hosts = {"127.0.0.1", "localhost"}
    _ip_mode_env = "LICENSE_MANAGER_ALLOW_IP_MODE"

    def _ip_mode_enabled(self):
        return (os.environ.get(self._ip_mode_env) or "").strip() == "1"

    def _normalize_addrport(self, addrport):
        value = (addrport or "").strip()
        if not value:
            return f"{self.default_addr}:{self.default_port}"

        if value.isdigit():
            host = self.default_addr
            port = value
        elif ":" in value:
            host, port = value.rsplit(":", 1)
            host = host or self.default_addr
        else:
            host = value
            port = self.default_port

        if port != self.default_port:
            raise CommandError(
                f"Only port {self.default_port} is allowed for this project. "
                f"Use {host}:{self.default_port}."
            )

        if not self._ip_mode_enabled() and host.lower() not in self._local_hosts:
            raise CommandError(
                f"Terminal mode allows only 127.0.0.1:{self.default_port}. "
                "IP mode is enabled only for installed application launch."
            )

        if host.lower() == "localhost":
            host = "127.0.0.1"

        return f"{host}:{port}"

    def handle(self, *args, **options):
        options["addrport"] = self._normalize_addrport(options.get("addrport"))
        return super().handle(*args, **options)
