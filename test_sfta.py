#!/usr/bin/env python3

"""
# test_sfta.py

Perform unit testing for `cmd.py`.

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import unittest

from sfta import Writ


class TestSfta(unittest.TestCase):
    def test_writ_conjunction(self):
        self.assertEqual(Writ.conjunction([]), 0)
        self.assertEqual(Writ.conjunction([0b101]), 0b101)
        self.assertEqual(Writ.conjunction([0b101011, 0b101011]), 0b101011)
        self.assertEqual(Writ.conjunction([0b10000, 0b00110]), 0b10110)
        self.assertEqual(Writ.conjunction([0b100, 0b010, 0b001]), 0b111)
        self.assertEqual(Writ.conjunction([0b1111, 0b0000, 0b001]), 0b1111)

    def test_writ_implies(self):
        self.assertTrue(Writ.implies(0b00100, 0b00000))
        self.assertTrue(Writ.implies(0b00011, 0b00001))
        self.assertTrue(Writ.implies(0b11111, 0b10011))
        self.assertFalse(Writ.implies(0b10000, 0b00100))
        self.assertFalse(Writ.implies(0b11001, 0b00111))


if __name__ == '__main__':
    unittest.main()
