import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"runtime"))
from ppaso_text import normalize_ppaso_text

class NumberPronunciation(unittest.TestCase):
    def test_decimal_keeps_fraction_digits_and_sentence_stop(self):
        self.assertEqual(normalize_ppaso_text("22.05도. 다음은 24도."), "22점영오도. 다음은 24도.")

    def test_negative_value_does_not_turn_positive(self):
        self.assertEqual(normalize_ppaso_text("영하 -1.5도, 음량 -1."), "영하 마이너스 1점오도, 음량 마이너스 1.")

    def test_negation_and_seat_are_untouched(self):
        text = "조수석은 그대로, 운전석만 바꾸지 않았어요."
        self.assertEqual(normalize_ppaso_text(text), text)

if __name__ == "__main__":
    unittest.main()
