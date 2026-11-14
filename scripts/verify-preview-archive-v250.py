#!/usr/bin/env python3
"""v250: verify the ACTUAL dashboard preview archive and serve its extracted files.
No third-party networking, market prices, or Pages deployment is involved.
"""
import argparse
import contextlib
import hashlib
import http.server
import json
import pathlib
import re
import tempfile
import threading
import urllib.request
import zipfile

MAX_FILES = 3000
MAX_UNCOMPRESSED = 75 * 1024 * 1024

def check_archive(archive_path: pathlib.Path) -> dict:
    with zipfile.ZipFile(archive_path, "r") as z:
        bad = z.testzip()
        if bad is not None:
            raise ValueError("Corrupt ZIP entry: " + bad)
        entries = z.infolist()
        if not entries or len(entries) > MAX_FILES:
            raise ValueError("Invalid file count")
        seen = set()
        total = 0
        for item in entries:
            pure = pathlib.PurePosixPath(item.filename)
            if (pure.is_absolute() or ".." in pure.parts or not pure.parts
                    or pure.parts[0] != "docs" or "\\" in item.filename):
                raise ValueError("Unsafe file path: " + item.filename)
            if item.filename in seen:
                raise ValueError("Duplicate path: " + item.filename)
            seen.add(item.filename)
            total += item.file_size
            if total > MAX_UNCOMPRESSED:
                raise ValueError("Archive too large")
            mode = (item.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("Symlinks are not allowed")
        required = {
            "docs/index.html",
            "docs/style.css",
            "docs/app.js",
            "docs/data/latest.json",
            "docs/data/sgx-four-pdf-replay-evidence-v248.json",
            "docs/data/sgx-uob-official-buyback-v242.json",
            "docs/data/sgx-ocbc-issuer-identity-v244.json",
            "docs/data/sgx-source-rights-review-v222.json",
            "docs/README-PREVIEW-v249.md",
        }
        if required - seen:
            raise ValueError("Preview missing files: " + repr(sorted(required - seen)))
        page = z.read("docs/index.html").decode("utf-8")
        sources = set(re.findall(r'<(?:script|link)\b[^>]*?(?:src|href)="\./([^"?#]+)"', page))
        if len(sources) < 25:
            raise ValueError("Insufficient HTML static assets")
        for source in sources:
            if (".." in pathlib.PurePosixPath(source).parts
                or "docs/" + source not in seen):
                raise ValueError("Missing or unsafe linked asset: " + source)
        feed = json.loads(z.read("docs/data/latest.json"))
        if (feed.get("ranking_enabled") is not False
            or feed.get("ranking_eligible_count") != 0
            or feed.get("coverage", {}).get("all_sgx_listed") is not False
            or feed["coverage"]["registered_count"] != len(feed["records"])):
            raise ValueError("Unsafe stock ranking state in preview")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            z.extractall(root)
            # Smoke HTTP without relying on the user's OS or an enabled Pages site.
            handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
                *args, directory=str(root), **kwargs
            )
            class QuietHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=str(root), **kwargs)
                def log_message(self, *args):
                    pass
            server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for relative in ("docs/", "docs/app.js", "docs/style.css",
                                 "docs/data/latest.json",
                                 "docs/data/sgx-four-pdf-replay-evidence-v248.json"):
                    url = f"http://127.0.0.1:{server.server_port}/{relative}"
                    with urllib.request.urlopen(url, timeout=10) as response:
                        if response.status != 200 or not response.read():
                            raise ValueError("Local HTTP smoke failed: " + relative)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)
        return {
            "schema_version": "value-hunter-preview-real-archive-smoke-v250",
            "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            "archive_files": len(entries),
            "html_static_assets_verified": len(sources),
            "local_http_smoke_passed": True,
            "feed_ranking_enabled": False,
            "ranking_eligible_count": 0,
            "github_pages_deployed_verified": False,
            "licensed_sgx_quotes_verified": False,
        }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path, default=pathlib.Path(
        "build/preview/dashboard-preview-smoke-v250.json"))
    args = parser.parse_args()
    report = check_archive(args.archive)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(f"v250 PASS: REAL ZIP verified ({report['archive_files']} files), "
          f"{report['html_static_assets_verified']} linked assets, "
          "localhost HTTP and ranking hold")

if __name__ == "__main__":
    main()
