#!/usr/bin/env python3

"""
# test_sfta.py

Perform unit testing for `cmd.py`.

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import textwrap
import unittest

from sfta import Event, FaultTree
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

    def test_fault_tree_is_bad_id(self):
        self.assertTrue(FaultTree.is_bad_id('Contains space'))
        self.assertTrue(FaultTree.is_bad_id('Contains\ttab'))
        self.assertTrue(FaultTree.is_bad_id('Contains,comma'))
        self.assertTrue(FaultTree.is_bad_id('Contains.full.stop'))

        self.assertFalse(FaultTree.is_bad_id('is_good'))
        self.assertFalse(FaultTree.is_bad_id('AbSoLUtEly-fiNe'))

    def test_fault_tree_parse(self):
        # Missing blank line before next object declaration
        self.assertRaises(
            FaultTree.ObjectDeclarationException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - probability: 1
                Event: B
                - probability: 0
            '''),
        )

        # Duplicate IDs
        self.assertRaises(
            FaultTree.DuplicateIdException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - probability: 1

                Event: A
                - probability: 1
            '''),
        )

        # Bad ID
        self.assertRaises(
            FaultTree.BadIdException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: This ID hath whitespace
                - probability: 1
            '''),
        )

        # Hanging property declaration
        self.assertRaises(
            FaultTree.PropertyDeclarationException,
            FaultTree.parse,
            textwrap.dedent('''
                - probability: 0
            '''),
        )

    def test_fault_tree_parse_event(self):
        # Label already set
        self.assertRaises(
            Event.LabelAlreadySetException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - label: First label
                - label: Second label
            '''),
        )

        # Setting probability after probability already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - probability: 0
                - probability: 0
            '''),
        )

        # Setting probability after rate already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - rate: 1
                - probability: 0
            '''),
        )

        # Setting rate after probability already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - probability: 0
                - rate: 1
            '''),
        )

        # Setting rate after rate already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - rate: 1
                - rate: 1
            '''),
        )

        # Bad float
        self.assertRaises(
            Event.BadFloatException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - rate: not-a-float
            '''),
        )

        # Bad probability (negative)
        self.assertRaises(
            Event.BadProbabilityException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - probability: -0.1
            '''),
        )

        # Bad probability (too big)
        self.assertRaises(
            Event.BadProbabilityException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - probability: 2
            '''),
        )

        # Bad rate (negative)
        self.assertRaises(
            Event.BadRateException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - rate: -1
            '''),
        )

        # Bad rate (too big)
        self.assertRaises(
            Event.BadRateException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - rate: inf
            '''),
        )

        # Unrecognised key
        self.assertRaises(
            Event.UnrecognisedKeyException,
            FaultTree.parse,
            textwrap.dedent('''
                Event: A
                - rate: 1
                - foo: bar
            '''),
        )


if __name__ == '__main__':
    unittest.main()
