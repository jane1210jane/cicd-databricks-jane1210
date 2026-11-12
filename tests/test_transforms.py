import unittest

from src.transforms import summarize_sales


class SummarizeSalesTests(unittest.TestCase):
    def test_combines_repeated_products_and_multiplies_quantity(self):
        rows = [("apple", 2, 120), ("banana", 3, 80), ("apple", 1, 120)]
        self.assertEqual(
            summarize_sales(rows), [("apple", 360), ("banana", 240)]
        )

    def test_empty_input(self):
        self.assertEqual(summarize_sales([]), [])

    def test_result_is_independent_of_input_order(self):
        rows = [("banana", 1, 80), ("apple", 1, 120)]
        self.assertEqual(
            summarize_sales(rows), [("apple", 120), ("banana", 80)]
        )


if __name__ == "__main__":
    unittest.main()
