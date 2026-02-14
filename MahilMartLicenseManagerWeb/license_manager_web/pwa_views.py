from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404


def _serve_static_file(relative_path, content_type):
    file_path = Path(settings.BASE_DIR) / "static" / relative_path
    if not file_path.exists():
        raise Http404("File not found.")

    response = FileResponse(file_path.open("rb"), content_type=content_type)
    response["Cache-Control"] = "no-cache"
    return response


def manifest(request):
    return _serve_static_file("manifest.webmanifest", "application/manifest+json")


def service_worker(request):
    return _serve_static_file("js/sw.js", "application/javascript")
