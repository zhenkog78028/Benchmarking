import unittest

from benchmark_workflow import validate_evaluation


class ValidateEvaluationTests(unittest.TestCase):
    def test_converts_100_point_scale_to_10_point_scale_without_rounding(self) -> None:
        self.assertEqual(validate_evaluation({"final_score": 85}), 8.5)

    def test_preserves_single_digit_scores_as_decimals(self) -> None:
        self.assertEqual(validate_evaluation({"final_score": 10}), 1.0)


if __name__ == "__main__":
    unittest.main()
