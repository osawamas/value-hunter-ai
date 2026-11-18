"""Download issuer financial PDF originals from a source-checked JSON manifest.

This is a local-only acquisition stage, not financial verification. Manifest:
[{"code":"1234","url":"https://issuer.example/report.pdf","sha256":"64 hex"}]
The operator must supply exact approved hostnames. No prices or APKs are published.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

CODE = re.compile(r"[0-9]{4}[0-9A-Z]?")
DIGEST = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 30 * 1024 * 1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect requires separate source verification")


def validate(entry, allowed_hosts):
    code, url, digest = entry["code"], entry["url"], entry["sha256"]
    parts = urlsplit(url)
    if not CODE.fullmatch(code) or not DIGEST.fullmatch(digest):
        raise ValueError("Invalid code or SHA256")
    if (parts.scheme != "https" or not parts.hostname
            or parts.hostname.lower() not in allowed_hosts
            or parts.username or parts.password or parts.port not in (None, 443)
            or parts.fragment):
        raise ValueError("Unapproved original URL")
    return code, url, digest


def fetch(entry, destination, allowed_hosts, opener=None):
    code, url, expected = validate(entry, allowed_hosts)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / (code + "-" + expected[:16] + ".pdf")
    # A manifest-approved cache must be a regular file, never a symlink.
    # Otherwise a malicious local entry could redirect validation to another path.
    if target.is_symlink():
        raise ValueError("Cached PDF symlink is not allowed")
    if target.exists() and not target.is_file():
        raise ValueError("Cached PDF is not a regular file")
    if target.exists():
        # A local cache must obey the same size bound as a network response.
        # Stream the digest instead of loading an untrusted large file into RAM.
        if target.stat().st_size > MAX_BYTES:
            raise ValueError("Existing PDF exceeds size limit")
        sha = hashlib.sha256()
        with target.open("rb") as cached:
            if cached.read(5) != b"%PDF-":
                raise ValueError("Existing PDF does not match manifest")
            cached.seek(0)
            for chunk in iter(lambda: cached.read(65536), b""):
                sha.update(chunk)
        if sha.hexdigest() == expected:
            return "cached"
        raise ValueError("Existing PDF does not match manifest")
    opener = opener or build_opener(NoRedirect())
    request = Request(url, headers={"User-Agent": "ValueHunterPrivateResearch/1.0"})
    temp = None
    try:
        with opener.open(request, timeout=25) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_BYTES:
                raise ValueError("PDF exceeds size limit")
            with tempfile.NamedTemporaryFile(dir=destination, delete=False) as out:
                temp = Path(out.name)
                sha = hashlib.sha256()
                size = 0
                first = True
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("PDF exceeds size limit")
                    if first and not chunk.startswith(b"%PDF-"):
                        raise ValueError("Response is not a PDF")
                    first = False
                    sha.update(chunk)
                    out.write(chunk)
                if first or sha.hexdigest() != expected:
                    raise ValueError("Original PDF SHA256 mismatch")
        os.replace(temp, target)
        temp = None
        return "downloaded"
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allowed-host", action="append", required=True)
    parser.add_argument("--report", type=Path, help="Private per-source acquisition audit JSON")
    args = parser.parse_args()
    hosts = {host.lower() for host in args.allowed_host}
    records = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        parser.error("Manifest must be a JSON array")
    counts = {"downloaded": 0, "cached": 0, "failed": 0}
    audit = []
    for entry in records:
        code = entry.get("code") if isinstance(entry, dict) else None
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        try:
            status = fetch(entry, args.output, hosts)
            counts[status] += 1
            audit.append({"code": code, "sha256": digest, "status": status})
        except (ValueError, OSError, KeyError, TypeError) as exc:
            counts["failed"] += 1
            audit.append({"code": code, "sha256": digest, "status": "failed",
                          "error_type": type(exc).__name__})
            print(f"Source rejected: {type(exc).__name__}", file=__import__("sys").stderr)
    summary = {"market": "JP", "source_records": len(records), **counts,
               "financial_records_verified": 0}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"summary": summary, "sources": audit},
                                          ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    if counts["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
