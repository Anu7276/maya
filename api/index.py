import os
import sys
from urllib.parse import parse_qs

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAYA_DIR = os.path.join(BASE_DIR, "maya_flask")

if MAYA_DIR not in sys.path:
    sys.path.insert(0, MAYA_DIR)

from app import app as flask_app  # noqa: E402


class PreserveRequestPath:
    """Restore the original URL path after Vercel's internal rewrite."""

    def __call__(self, environ, start_response):
        requested_path = parse_qs(environ.get("QUERY_STRING", "")).get(
            "__maya_path", [None]
        )[0]
        if requested_path:
            environ["PATH_INFO"] = requested_path
        return flask_app(environ, start_response)


app = PreserveRequestPath()

