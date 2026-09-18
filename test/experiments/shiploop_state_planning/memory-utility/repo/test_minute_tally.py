import unittest

import minute_tally


class ActivityLabelsTest(unittest.TestCase):
    def test_returns_labels_in_source_order(self):
        self.assertEqual(
            minute_tally.activity_labels(minute_tally.ACTIVITIES),
            ["warmup", "practice", "review"],
        )


if __name__ == "__main__":
    unittest.main()

