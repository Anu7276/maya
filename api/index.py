import os
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAYA_DIR = os.path.join(BASE_DIR, "maya_flask")

if MAYA_DIR not in sys.path:
    sys.path.insert(0, MAYA_DIR)

from app import app  # noqa: E402

