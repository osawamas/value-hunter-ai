"""Resume JPX financial evidence batches without silently losing corrections."""
import json
import os
import tempfile
from pathlib import Path

def merge_checkpoint(previous, incoming):
    universe = previous.get("universe")
    if not isinstance(universe, list) or len(universe) != len(set(universe)):
        raise ValueError("invalid universe")
    if incoming.get("universe") != universe:
        raise ValueError("universe/order changed")
    def index(rows):
        result = {}
        for row in rows:
            if not isinstance(row, dict) or row.get("ticker") not in universe or row["ticker"] in result:
                raise ValueError("unknown/duplicate ticker")
            revision = row.get("revision", 0)
            if type(revision) is not int or revision < 0:
                raise ValueError("invalid revision")
            result[row["ticker"]] = row
        return result
    old = index(previous.get("records", []))
    for ticker, row in index(incoming.get("records", [])).items():
        prior = old.get(ticker)
        if prior is None:
            old[ticker] = row
        elif row == prior:
            continue
        elif row["revision"] > prior.get("revision", 0) and row.get("source_url") and row.get("source_sha256"):
            old[ticker] = row
        else:
            raise ValueError("stale/conflicting/unverified correction: " + ticker)
    return {"universe": universe,
            "records": [old[t] for t in universe if t in old],
            "next_ticker": next((t for t in universe if t not in old), None)}

def save_atomic(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
