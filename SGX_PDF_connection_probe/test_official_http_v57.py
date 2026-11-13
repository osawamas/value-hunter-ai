"""No external network used; issuer HTTP errors remain transparent."""
import io
import unittest
import urllib.error
from official_http_v57 import get_pdf


class Response:
    def __init__(self,data): self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):return None
    def read(self,limit):return self.data[:limit]


def http_error(code):
    return urllib.error.HTTPError("https://example.com/file.pdf",code,"test",{},None)


class IssuerHttpTests(unittest.TestCase):
    def test_success_accepts_pdf(self):
        result=get_pdf("https://example.com/issuer.pdf",
                       open_url=lambda req,timeout:Response(b"%PDF-test"),sleep=lambda t:None)
        self.assertEqual(result,b"%PDF-test")
    def test_403_does_not_retry(self):
        calls=[]
        def blocked(req,timeout):
            calls.append(1)
            raise http_error(403)
        with self.assertRaisesRegex(PermissionError,"403_ACCESS_DENIED"):
            get_pdf("https://example.com/issuer.pdf",open_url=blocked,sleep=lambda t:None)
        self.assertEqual(len(calls),1)
    def test_transient_503_retries_only_twice(self):
        calls=[]
        def sometimes(req,timeout):
            calls.append(1)
            if len(calls)<3:raise http_error(503)
            return Response(b"%PDF-real")
        result=get_pdf("https://example.com/issuer.pdf",open_url=sometimes,sleep=lambda t:None)
        self.assertEqual(result,b"%PDF-real")
        self.assertEqual(len(calls),3)
    def test_404_not_retried(self):
        calls=[]
        def missing(req,timeout):
            calls.append(1);raise http_error(404)
        with self.assertRaises(ConnectionError):
            get_pdf("https://example.com/issuer.pdf",open_url=missing,sleep=lambda t:None)
        self.assertEqual(len(calls),1)
    def test_non_pdf_rejected(self):
        with self.assertRaises(ValueError):
            get_pdf("https://example.com/issuer.pdf",
                    open_url=lambda req,timeout:Response(b"<html>Not PDF</html>"))
    def test_oversize_rejected(self):
        with self.assertRaises(ValueError):
            get_pdf("https://example.com/issuer.pdf",max_bytes=8,
                    open_url=lambda req,timeout:Response(b"%PDF-123456"))
    def test_insecure_url_rejected(self):
        with self.assertRaises(ValueError):
            get_pdf("http://example.com/issuer.pdf")
if __name__=="__main__":unittest.main()
