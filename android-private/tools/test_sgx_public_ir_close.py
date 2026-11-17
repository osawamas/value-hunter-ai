from datetime import date
from decimal import Decimal
import unittest
from urllib.parse import parse_qs

from sgx_public_ir_close import lookup_data, read_close

SESSION = date(2026, 11, 13)
ROW = "<tr><td>Nov 13, 2026</td><td><span>$12.34</span></td><td>1:1</td></tr>"


def table(rows):
    return (
        '<table class="nirtable historical-lookup"><thead><tr>'
        '<th>Date Requested</th><th>Closing Price</th><th>Split Adjustment Factor</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
    )


class PublicIrCloseTest(unittest.TestCase):
    def test_reads_close_for_requested_date_only(self):
        self.assertEqual(read_close(table(ROW), SESSION), Decimal("12.34"))
        self.assertIsNone(read_close(table(ROW), date(2026, 11, 17)))

    def test_rejects_duplicate_dates(self):
        with self.assertRaisesRegex(ValueError, "multiple rows"):
            read_close(table(ROW + ROW), SESSION)

    def test_rejects_html_shell_and_truncated_table(self):
        for html in ("<main>Loading...</main>", table(ROW).removesuffix("</table>")):
            with self.subTest(html=html), self.assertRaisesRegex(ValueError, "complete"):
                read_close(html, SESSION)

    def test_rejects_last_trade_as_close(self):
        with self.assertRaisesRegex(ValueError, "headers changed"):
            read_close(table(ROW).replace("Closing Price", "Last Price"), SESSION)

    def test_rejects_invalid_or_zero_close(self):
        for value in ("N/A", "$0.00", "$12,34.00"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                read_close(table(ROW.replace("$12.34", value)), SESSION)

    def test_submits_the_public_forms_current_field_names_and_requested_date(self):
        fields = (
            '<input name="form_build_id" value="form-example">'
            '<input name="form_id" value="historical_lookup_form">'
            '<input name="op" value="Submit">'
            '<input name="ignore" value="not-sent">'
            '<select name="current[SGXL_SI][date_month]"></select>'
            '<select name="current[SGXL_SI][date_day]"></select>'
            '<select name="current[SGXL_SI][date_year]"></select>'
        )
        form = (
            '<form id="historical-lookup-form" action="/stock-information/historic-stock-lookup" '
            f'method="post">{fields}</form>'
        )
        data = parse_qs(lookup_data(form, date(2026, 4, 2)).decode())
        self.assertEqual(data, {
            "form_build_id": ["form-example"], "form_id": ["historical_lookup_form"], "op": ["Submit"],
            "current[SGXL_SI][date_month]": ["04"], "current[SGXL_SI][date_day]": ["2"],
            "current[SGXL_SI][date_year]": ["2026"],
        })
        with self.assertRaisesRegex(ValueError, "unexpected date lookup action"):
            lookup_data(form.replace('action="/stock-information', 'action="https://example.com'), SESSION)


if __name__ == "__main__":
    unittest.main()
