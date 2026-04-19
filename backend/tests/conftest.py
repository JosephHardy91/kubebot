import sys
import os
from unittest.mock import MagicMock

# Add the backend directory to sys.path so tests can import project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Stub out heavy ETL dependencies (dagster, psycopg2) that are not needed for
# unit-testing pure functions.  These stubs must be in place before any project
# module is imported.
for mod_name in (
    "dagster",
    "dagster_webserver",
    "psycopg2",
    "psycopg2.extras",
):
    sys.modules.setdefault(mod_name, MagicMock())
