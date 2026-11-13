"""Conservative issuer-PDF HTTP client with explicit 403 handling.

Only transient 429/5xx responses are retried (at most two retries).
Never bypass access controls, fabricate PDF contents or accept stale cached
content as a new issuer download.
"""
import time
import urllib.error
import urllib.request


TRANSIENT={429,500,502,503,504}


def get_pdf(url, *, max_bytes=25_000_000, timeout=60, retries=2,
            open_url=None, sleep=None):
    if not isinstance(url,str) or not url.startswith("https://"):
        raise ValueError("OFFICIAL_PDF_URL_NOT_HTTPS")
    if max_bytes<=0 or not 0<=retries<=2:
        raise ValueError("OFFICIAL_PDF_LIMITS_INVALID")
    if open_url is None:
        open_url=urllib.request.urlopen
    if sleep is None:
        sleep=time.sleep
    request=urllib.request.Request(
        url, headers={"User-Agent":"Mozilla/5.0 (VALUE-HUNTER-AI issuer filing research)",
                      "Accept":"application/pdf"})
    for attempt in range(retries+1):
        try:
            with open_url(request,timeout=timeout) as response:
                data=response.read(max_bytes+1)
            if len(data)>max_bytes:
                raise ValueError("OFFICIAL_PDF_OVERSIZE")
            if not data.startswith(b"%PDF"):
                raise ValueError("OFFICIAL_PDF_CONTENT_INVALID")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code==403:
                raise PermissionError("OFFICIAL_PDF_HTTP_403_ACCESS_DENIED") from exc
            if exc.code not in TRANSIENT or attempt==retries:
                raise ConnectionError(f"OFFICIAL_PDF_HTTP_{exc.code}") from exc
            retry_after=exc.headers.get("Retry-After","") if exc.headers else ""
            try:
                delay=min(max(float(retry_after),1),5)
            except (ValueError,TypeError):
                delay=attempt+1
            sleep(delay)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt==retries:
                raise ConnectionError("OFFICIAL_PDF_NETWORK_UNAVAILABLE") from exc
            sleep(attempt+1)
    raise RuntimeError("Unreachable issuer PDF HTTP retry state")
