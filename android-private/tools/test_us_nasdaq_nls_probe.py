from decimal import Decimal
from io import BytesIO
from struct import pack
import unittest

from us_nasdaq_nls_probe import compare_price_sets, inspect_capture, inspect_tape_c


def trade(ticker, price, modifier=b"M", *, origin=b"Q", listing=b"Q"):
    report = bytearray(57)
    report[0:1] = b"e"
    report[17:18] = origin
    report[18:26] = ticker.encode("ascii").ljust(8)
    report[26:27] = listing
    report[37:45] = price.to_bytes(8, "big")
    report[56:57] = modifier
    return bytes(report)


def capture(messages):
    payload = b"SESSION123" + pack(">QH", 1, len(messages))
    payload += b"".join(pack(">H", len(message)) + message for message in messages)
    ethernet = bytes(12) + b"\x81\x00\x00\x01\x08\x00"
    ip = b"\x45\x00" + pack(">H", 28 + len(payload)) + bytes(5) + b"\x11" + bytes(10)
    udp = pack(">HHHH", 1, 2, len(payload) + 8, 0)
    frame = ethernet + ip + udp + payload
    header = bytes.fromhex("4d3cb2a1") + pack("<HHIIII", 2, 4, 0, 0, 262144, 1)
    return header + pack("<IIII", 1772553600, 0, len(frame), len(frame)) + frame


class NasdaqNlsProbeTest(unittest.TestCase):
    def test_only_nasdaq_nocp_reports_are_counted_and_conflicts_are_visible(self):
        result = inspect_capture(capture([
            trade("AAPL", 123456), trade("AAPL", 123456),
            trade("NVDA", 456780), trade("NVDA", 456789),
            trade("MSFT", 100000, b"o"), trade("MSFT", 100000, origin=b"L"),
            trade("IBM", 200000, listing=b"N"),
        ]))
        self.assertEqual(7, result["trade_reports"])
        self.assertEqual(4, result["nasdaq_listed_nocp_reports"])
        self.assertEqual(["AAPL"], result["unambiguous_nocp_symbols"])
        self.assertEqual(["NVDA"], result["conflicting_nocp_symbols"])

    def test_truncated_packet_cannot_be_reported_as_no_official_closes(self):
        with self.assertRaisesRegex(ValueError, "Truncated"):
            inspect_capture(capture([trade("AAPL", 123456)])[:-1])


    def test_tape_c_distinguishes_official_trade_from_consolidated_summary(self):
        start = bytes(8) + b"SO"
        end = bytes(8) + b"SC"
        summary = bytearray(42)
        summary[8:18] = b"JAAPL    Q"
        summary[26:30] = (1230000).to_bytes(4, "big")
        trade_report = bytearray(49)
        trade_report[8:19] = b"TQAAPL    Q"
        trade_report[29:33] = (1230123).to_bytes(4, "big")
        trade_report[40:41] = b"M"
        framed = b"".join(pack(">H", len(record)) + record for record in (start, summary, trade_report, end))
        summaries, official = inspect_tape_c(BytesIO(framed))
        self.assertEqual({"AAPL": {1230000}}, summaries)
        self.assertEqual({"AAPL": {1230123}}, official)
        with self.assertRaisesRegex(ValueError, "start and end"):
            inspect_tape_c(BytesIO(framed[:-12]))


    def test_full_dolt_comparison_reports_exception_tickers_without_price_values(self):
        reference = {symbol: Decimal("10.00") for symbol in ("EXACT", "CENT", "DIFF", "NULL", "ABSENT")}
        prices = {"EXACT": 10.0, "CENT": 10.01, "DIFF": 10.02}
        result = compare_price_sets(reference, prices, prices.keys() | {"NULL"})
        self.assertEqual(1, result["exact_matches"])
        self.assertEqual(2, result["within_one_cent"])
        self.assertEqual(2, result["missing_dolt"])
        self.assertEqual({
            "no_dolt_row": ["ABSENT"],
            "dolt_row_without_usable_close": ["NULL"],
            "differ_over_one_cent": ["DIFF"],
        }, result["exceptions"])
