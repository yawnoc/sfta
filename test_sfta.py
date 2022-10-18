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
        # (Empty conjunction) = True
        self.assertEqual(Writ.conjunction([]), 0)

        # AC = AC
        self.assertEqual(Writ.conjunction([0b00101]), 0b00101)

        # True . A = A
        self.assertEqual(Writ.conjunction([0b00000, 0b00001]), 0b00001)

        # ABE . BC = ABCE
        self.assertEqual(Writ.conjunction([0b10011, 0b00110]), 0b10111)

        # C . A . B = ABC
        self.assertEqual(Writ.conjunction([0b100, 0b001, 0b010]), 0b111)

        # ABCD . True . A = ABCD
        self.assertEqual(Writ.conjunction([0b1111, 0b0000, 0b0001]), 0b1111)

    def test_writ_implies(self):
        # C implies True
        self.assertTrue(Writ.implies(0b00100, 0b00000))

        # AB implies A
        self.assertTrue(Writ.implies(0b00011, 0b00001))

        # ABCDE implies ABE
        self.assertTrue(Writ.implies(0b11111, 0b10011))

        # E does not imply C (due to C)
        self.assertFalse(Writ.implies(0b10000, 0b00100))

        # ADE does not imply ABC (due to BC)
        self.assertFalse(Writ.implies(0b11001, 0b00111))


if __name__ == '__main__':
    unittest.main()
