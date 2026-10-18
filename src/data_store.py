from json import loads, dump
from os import fsync, path, replace, remove
from tempfile import NamedTemporaryFile
from threading import Lock

DATA_FILE = "data/data.json"

# data.json is shared by GuildData ("guilds") and DitAnnouncements ("last_update", "seen").
# Every change re-reads the file under this lock and only touches the caller's keys,
# so neither side can overwrite the other's changes with a stale copy.
_lock = Lock()

def _load() -> dict:
    with open(DATA_FILE, "r") as file:
        return loads(file.read())

def _write(data: dict):
    """ Writes to a temp file in the same directory and swaps it in, so data.json is never half written """
    tmp = NamedTemporaryFile("w", dir=path.dirname(DATA_FILE), prefix=".data.", suffix=".json", delete=False)
    try:
        with tmp:
            dump(data, tmp, indent=4)
            tmp.flush()
            fsync(tmp.fileno())
        replace(tmp.name, DATA_FILE)
    except:
        if path.exists(tmp.name):
            remove(tmp.name)
        raise

def read() -> dict:
    with _lock:
        return _load()

def update(change) -> dict:
    """ Re-reads data.json, applies change(data) to it and writes it back. Returns the new data. """
    with _lock:
        data = _load()
        change(data)
        _write(data)
        return data
