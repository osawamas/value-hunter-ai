from datetime import date
import unittest

from jpx_monthly_close_history import Links, months_ending, read_month

HEADER = "Date Average Closing Price\n"
ROW = "2026/10   1301   極洋 普通株式   4,620.00 1 4,660.00 26 4,415.00 8 4,560.00 30 4,521.90\n"


class MonthlyHistoryTest(unittest.TestCase):
    def test_reads_close_not_average_and_refuses_a_conflicting_split_row(self):
        month = date(2026, 10, 1)
        prices, ambiguous = read_month(HEADER + ROW, month, ["1301", "3861"])
        self.assertEqual(prices, {"1301": {"session": "2026-10-30", "close": "4560.00"}})
        self.assertEqual(ambiguous, [])
        self.assertEqual(read_month(HEADER + ROW + ROW.replace("4,560.00", "2,280.00"), month, ["1301"]),
                         ({}, ["1301"]))

    def test_five_year_window_and_archive_option(self):
        months = list(months_ending(date(2026, 10, 1), 60))
        self.assertEqual((len(months), months[-1]), (60, date(2021, 11, 1)))
        index = Links()
        index.feed('<option value="/markets/statistics-equities/price/00-archives-05.html">2021年</option>')
        self.assertTrue(index.archives["2021"].endswith("00-archives-05.html"))
