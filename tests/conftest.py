import sqlite3

import pytest

from quran_harness import index, ingest, readings, segmentation, units


@pytest.fixture(scope="session")
def built_db(tmp_path_factory):
    """The whole database (steps 2 to 7), built once from the raw files."""
    path = tmp_path_factory.mktemp("db") / "quran.db"
    ingest.build(path)
    index.build(path)
    units.build(path)
    segmentation.build(path)
    readings.build(path)
    return path


@pytest.fixture(scope="module")
def db(built_db):
    connection = sqlite3.connect(built_db)
    yield connection
    connection.close()
