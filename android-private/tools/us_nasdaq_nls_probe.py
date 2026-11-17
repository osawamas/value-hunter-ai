"""Inspect Nasdaq NLS samples for official and consolidated close reports."""
import argparse
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
import gzip
import json
import re
from pathlib import Path
from struct import unpack_from
from zoneinfo import ZoneInfo

from us_public_files_probe import MAX_BYTES, SYMBOL, dolt_rows, validated_closes

PCAP_ENDIAN = {
    bytes.fromhex(magic): endian for magic, endian in (
        ("d4c3b2a1", "<"), ("4d3cb2a1", "<"),
        ("a1b2c3d4", ">"), ("a1b23c4d", ">"),
    )
}
EASTERN = ZoneInfo("America/New_York")


def udp_datagrams(content):
    endian = PCAP_ENDIAN.get(content[:4])
    if endian is None or len(content) < 24:
        raise ValueError("Expected a classic PCAP capture")
    version_major, version_minor = unpack_from(endian + "HH", content, 4)
    if (version_major, version_minor) != (2, 4) or unpack_from(endian + "I", content, 20)[0] != 1:
        raise ValueError("Expected PCAP 2.4 with Ethernet frames")
    offset = 24
    while offset < len(content):
        if len(content) - offset < 16:
            raise ValueError("Truncated PCAP packet header")
        seconds, _, captured, original = unpack_from(endian + "IIII", content, offset)
        offset += 16
        if captured != original or not 14 <= captured <= len(content) - offset:
            raise ValueError("Truncated or invalid Ethernet frame")
        frame = content[offset:offset + captured]
        offset += captured
        ethertype, ip = frame[12:14], 14
        while ethertype in (b"\x81\x00", b"\x88\xa8"):
            if len(frame) < ip + 4:
                raise ValueError("Truncated VLAN header")
            ethertype, ip = frame[ip + 2:ip + 4], ip + 4
        if ethertype != b"\x08\x00":
            continue
        if len(frame) < ip + 20:
            raise ValueError("Truncated IPv4 header")
        if frame[ip + 9] != 17:
            continue
        ihl = 4 * (frame[ip] & 15)
        ip_length = int.from_bytes(frame[ip + 2:ip + 4], "big")
        fragments = int.from_bytes(frame[ip + 6:ip + 8], "big")
        if frame[ip] >> 4 != 4 or ihl < 20 or fragments & 0x3FFF or not ihl + 8 <= ip_length <= len(frame) - ip:
            raise ValueError("Invalid or fragmented IPv4 UDP packet")
        udp = ip + ihl
        if int.from_bytes(frame[udp + 4:udp + 6], "big") != ip_length - ihl:
            raise ValueError("Invalid UDP payload length")
        yield seconds, frame[udp + 8:ip + ip_length]


def mold_messages(datagram):
    if len(datagram) < 20:
        raise ValueError("Truncated MoldUDP64 header")
    count = int.from_bytes(datagram[18:20], "big")
    offset = 20
    for _ in range(0 if count == 0xFFFF else count):
        length = int.from_bytes(datagram[offset:offset + 2], "big")
        offset += 2
        if not 0 < length <= len(datagram) - offset:
            raise ValueError("Truncated MoldUDP64 message")
        yield datagram[offset:offset + length]
        offset += length
    if offset != len(datagram):
        raise ValueError("Unexpected bytes after MoldUDP64 messages")


def inspect_capture(content):
    if len(content) > MAX_BYTES:
        raise ValueError("Use a bounded Nasdaq NLS test capture")
    dates = set()
    prices = defaultdict(set)
    trade_reports = official_reports = 0
    for seconds, payload in udp_datagrams(content):
        dates.add(datetime.fromtimestamp(seconds, EASTERN).date().isoformat())
        for message in mold_messages(payload):
            if message[:1] != b"e":
                continue
            if len(message) not in (57, 65):
                raise ValueError("Unexpected NLS 4.0 trade report length")
            trade_reports += 1
            if message[17:18] != b"Q" or message[26:27] != b"Q" or message[56:57] != b"M":
                continue
            ticker = message[18:26].decode("ascii").rstrip(" ")
            price = int.from_bytes(message[37:45], "big")
            if not SYMBOL.fullmatch(ticker) or price <= 0:
                raise ValueError("Invalid Nasdaq official close report")
            prices[ticker].add(price)
            official_reports += 1
    if len(dates) != 1 or not trade_reports:
        raise ValueError("Expected NLS 4.0 trade reports from a single capture date")
    return {
        "capture_date_et": min(dates),
        "trade_reports": trade_reports,
        "nasdaq_listed_nocp_reports": official_reports,
        "unambiguous_nocp_symbols": sorted(ticker for ticker, values in prices.items() if len(values) == 1),
        "conflicting_nocp_symbols": sorted(ticker for ticker, values in prices.items() if len(values) > 1),
    }


def inspect_tape_c(stream):
    summaries = defaultdict(set)
    official = defaultdict(set)
    events = []
    while header := stream.read(2):
        length = int.from_bytes(header, "big")
        if len(header) != 2 or not 9 <= length <= 1024:
            raise ValueError("Invalid NLS Plus record length")
        message = stream.read(length)
        if len(message) != length:
            raise ValueError("Truncated NLS Plus record")
        kind = message[8:9]
        if kind == b"S" and length == 10:
            events.append(message[9:10])
        if kind in (b"J", b"j"):
            size, left, right = (42, 26, 30) if kind == b"J" else (58, 34, 42)
            if length != size:
                raise ValueError("Unexpected NLS Plus daily summary length")
            if message[17:18] == b"Q":
                record_price(summaries, message[9:17], message[left:right])
        elif kind in (b"T", b"t"):
            size, right = (49, 33) if kind == b"T" else (53, 37)
            if length != size:
                raise ValueError("Unexpected NLS Plus trade report length")
            modifier = right + 7
            if message[9:10] == b"Q" and message[18:19] == b"Q" and message[modifier:modifier + 1] == b"M":
                record_price(official, message[10:18], message[29:right])
    if not events or events[0] != b"O" or events[-1] != b"C" or events.count(b"O") != 1:
        raise ValueError("Expected one NLS Plus session with system start and end")
    return summaries, official


def record_price(target, raw_symbol, raw_value):
    symbol = raw_symbol.decode("ascii").rstrip(" ")
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid NLS Plus symbol")
    value = int.from_bytes(raw_value, "big")
    if value:
        target[symbol].add(value)


def compare_price_sets(reference, prices):
    matched = reference.keys() & prices.keys()
    within = sum(abs(reference[symbol] - Decimal(str(prices[symbol]))) <= Decimal("0.01")
                 for symbol in matched)
    return {
        "matched": len(matched), "within_one_cent": within,
        "differ_over_one_cent": len(matched) - within, "missing_dolt": len(reference) - len(matched),
    }


def inspect_archive(path, dolt_directory=None):
    named_date = re.fullmatch(r"(\d{8})_nlsplus_tape_c\.gz", path.name)
    if not named_date:
        raise ValueError("Use the original dated NLS Plus Tape C sample filename")
    day = datetime.strptime(named_date[1], "%m%d%Y").date()
    with gzip.open(path, "rb") as stream:
        summaries, official = inspect_tape_c(stream)
    result = {"trade_date_from_filename": day.isoformat()}
    prices = None
    if dolt_directory is not None and (summaries or official):
        _, prices = validated_closes(day, dolt_rows(dolt_directory, day))
    for label, records in (("consolidated_close", summaries), ("nocp_trade_reports", official)):
        reference = {symbol: Decimal(next(iter(values))).scaleb(-4)
                     for symbol, values in records.items() if len(values) == 1}
        result[label] = {
            "symbols": len(reference),
            "conflicting_symbols": sorted(symbol for symbol, values in records.items() if len(values) > 1),
        }
        if prices is not None:
            result[label]["dolt_comparison"] = compare_price_sets(reference, prices)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--tape-c", action="store_true", help="Inspect a dated NLS Plus 3.0 Tape C gzip sample")
    parser.add_argument("--dolt-dir", type=Path, help="Optional local Dolt mirror for the Tape C comparison")
    args = parser.parse_args()
    if args.dolt_dir is not None and not args.tape_c:
        parser.error("--dolt-dir requires --tape-c")
    try:
        if args.tape_c:
            result = inspect_archive(args.capture, args.dolt_dir)
        else:
            with args.capture.open("rb") as file:
                result = inspect_capture(file.read(MAX_BYTES + 1))
    except (EOFError, OSError, ValueError) as error:
        parser.exit(1, f"Nasdaq NLS inspection failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
