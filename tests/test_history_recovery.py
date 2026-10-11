import unittest
from scripts.recover_history import validate

class HistoryTests(unittest.TestCase):
    def test_sorted_deduplicated_exact_coverage(self):
        rows=[[300,90,110,100,105,10],[0,90,110,100,105,10]]
        selected,missing=validate(rows+rows,0,600,300)
        self.assertEqual([r[0] for r in selected],[0,300]); self.assertEqual(missing,[])
    def test_missing_bar_never_filled(self):
        selected,missing=validate([[0,90,110,100,105,10]],0,600,300)
        self.assertEqual(missing,[300]);self.assertEqual(len(selected),1)
    def test_conflicting_duplicate_rejected(self):
        with self.assertRaises(ValueError):validate([[0,90,110,100,105,10],[0,90,110,100,104,10]],0,300,300)
    def test_invalid_ohlc_rejected(self):
        with self.assertRaises(ValueError):validate([[0,90,99,100,105,10]],0,300,300)
    def test_outside_window_not_promoted(self):
        selected,missing=validate([[600,90,110,100,105,10]],0,300,300)
        self.assertEqual(selected,[]);self.assertEqual(missing,[0])
