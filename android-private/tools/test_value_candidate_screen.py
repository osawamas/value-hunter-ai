from decimal import Decimal
import unittest

from value_candidate_screen import classify, range_position


def values(*args):
    return tuple(Decimal(str(x)) if x is not None else None for x in args)


class CandidateScreenTest(unittest.TestCase):
    def test_budget_boundaries_and_currency(self):
        hit = classify(*values(10, 100, 15, 1), False)
        self.assertEqual((hit.tier, hit.quantity, hit.yen_cost), ("priority", 100, 100000))
        single = classify(*values(1000.01, 1, 14, 1), True)
        self.assertEqual((single.tier, single.quantity), ("priority", 1))
        self.assertEqual(classify(*values(1000.01, 1, 14, 1), False).tier, "excluded")

    def test_accepts_one_ratio_without_mistaking_missing_data_or_losses_for_value(self):
        self.assertEqual(classify(*values(700, 1, 14, None), False).tier, "reference")
        self.assertEqual(classify(*values(700, 1, 19, 0.8), False).tier, "reference")
        self.assertEqual(classify(*values(700, 1, 30, 0.8), False).tier, "excluded")
        self.assertEqual(classify(*values(700, 1, -6, 0.8), False).tier, "held")
        self.assertEqual(classify(*values(700, 1, None, None), False).tier, "held")

    def test_history_provides_position_without_changing_eligibility(self):
        self.assertEqual(range_position(Decimal("90"), values(60, 100, 120)), Decimal("0.5"))
        self.assertIsNone(range_position(Decimal("90"), values(60, 60)))
        self.assertIsNone(range_position(Decimal("90"), values(60, None)))
