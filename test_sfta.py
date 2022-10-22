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

from sfta import Event, FaultTree, Gate
from sfta import Writ
from sfta import find_cycles


class TestSfta(unittest.TestCase):
    def test_find_cycle(self):
        self.assertEqual(
            find_cycles({}),
            set()
        )
        self.assertEqual(
            find_cycles({
                1: {3, 4},
                2: {4},
                3: {4, 5},
                4: {5},
                5: {6, 7},
            }),
            set(),
        )
        self.assertEqual(
            find_cycles({
                1: {1},
                2: {3},
                3: {2}},
            ),
            {(1,), (2, 3)}
        )
        self.assertEqual(
            find_cycles({
                1: {2, 3},
                3: {4},
                4: {5},
                5: {6},
                6: {4},
            }),
            {(4, 5, 6)},
        )
        self.assertEqual(
            find_cycles({
                1: {2},
                2: {5},
                3: {2},
                4: {1, 2},
                5: {4, 6},
                6: {3, 6},
            }),
            {(1, 2, 5, 4), (2, 5, 4), (6,), (2, 5, 6, 3)},
        )

    def test_writ_and(self):
        # (Empty conjunction) = True
        self.assertEqual(Writ.and_(), 0)

        # AC = AC
        self.assertEqual(Writ.and_(0b00101), 0b00101)

        # True . A = A
        self.assertEqual(Writ.and_(0b00000, 0b00001), 0b00001)

        # ABE . BC = ABCE
        self.assertEqual(Writ.and_(0b10011, 0b00110), 0b10111)

        # C . A . B = ABC
        self.assertEqual(Writ.and_(0b100, 0b001, 0b010), 0b111)

        # ABCD . True . A = ABCD
        self.assertEqual(Writ.and_(0b1111, 0b0000, 0b0001), 0b1111)

    def test_writ_implies(self):
        # C implies True
        self.assertTrue(Writ.implieth(0b00100, 0b00000))

        # AB implies A
        self.assertTrue(Writ.implieth(0b00011, 0b00001))

        # ABCDE implies ABE
        self.assertTrue(Writ.implieth(0b11111, 0b10011))

        # E does not imply C (due to C)
        self.assertFalse(Writ.implieth(0b10000, 0b00100))

        # ADE does not imply ABC (due to BC)
        self.assertFalse(Writ.implieth(0b11001, 0b00111))

    def test_gate_split_ids(self):
        self.assertEqual(Gate.split_ids(''), [])
        self.assertEqual(Gate.split_ids('abc'), ['abc'])
        self.assertEqual(Gate.split_ids('abc DEF'), ['abc DEF'])

        self.assertEqual(Gate.split_ids(','), [])
        self.assertEqual(Gate.split_ids('abc,DEF'), ['abc', 'DEF'])
        self.assertEqual(Gate.split_ids('abc, DEF,'), ['abc', 'DEF'])

    def test_fault_tree_is_bad_id(self):
        self.assertTrue(FaultTree.is_bad_id('Contains space'))
        self.assertTrue(FaultTree.is_bad_id('Contains\ttab'))
        self.assertTrue(FaultTree.is_bad_id('Contains,comma'))
        self.assertTrue(FaultTree.is_bad_id('Contains.full.stop'))

        self.assertFalse(FaultTree.is_bad_id('is_good'))
        self.assertFalse(FaultTree.is_bad_id('AbSoLUtEly-fiNe'))

    def test_fault_tree_build(self):
        # Missing blank line before next object declaration
        self.assertRaises(
            FaultTree.SmotheredObjectDeclarationException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - probability: 1
                # Comments don't count as a blank line
                Event: B
                - probability: 0
            '''),
        )

        # Duplicate IDs
        self.assertRaises(
            FaultTree.DuplicateIdException,
            FaultTree.build,
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
            FaultTree.build,
            textwrap.dedent('''
                Event: This ID hath whitespace
                - probability: 1
            '''),
        )

        # Dangling property declaration
        self.assertRaises(
            FaultTree.DanglingPropertySettingException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - probability: 1

                # Dangling:
                - probability: 0
            '''),
        )

        # Bad line
        self.assertRaises(
            FaultTree.BadLineException,
            FaultTree.build,
            'foo bar',
        )
        self.assertRaises(
            FaultTree.BadLineException,
            FaultTree.build,
            'Event:',
        )
        self.assertRaises(
            FaultTree.BadLineException,
            FaultTree.build,
            'Gate: ',
        )
        self.assertRaises(
            FaultTree.BadLineException,
            FaultTree.build,
            'Event:A',
        )
        self.assertRaises(
            FaultTree.BadLineException,
            FaultTree.build,
            ' - key: value',
        )

        # Unrecognised Key
        self.assertRaises(
            FaultTree.UnrecognisedKeyException,
            FaultTree.build,
            '- foo: bar',
        )

        # Circular gate inputs
        self.assertRaises(
            FaultTree.CircularGateInputsException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - type: AND
                - inputs: A
            '''),
        )
        self.assertRaises(
            FaultTree.CircularGateInputsException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: Paper
                - type: OR
                - inputs: Scissors, Lizard

                Gate: Scissors
                - type: OR
                - inputs: Spock, Rock

                Gate: Spock
                - type: OR
                - inputs: Lizard, Paper

                Gate: Lizard
                - type: OR
                - inputs: Rock, Scissors

                Gate: Rock
                - type: OR
                - inputs: Paper, Spock
            '''),
        )

    def test_fault_tree_build_event(self):
        # Label already set
        self.assertRaises(
            Event.LabelAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - label: First label
                - label: Second label
            '''),
        )

        # Setting probability after probability already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - probability: 0
                - probability: 0
            '''),
        )

        # Setting probability after rate already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - rate: 1
                - probability: 0
            '''),
        )

        # Setting rate after probability already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - probability: 0
                - rate: 1
            '''),
        )

        # Setting rate after rate already set
        self.assertRaises(
            Event.QuantityAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - rate: 1
                - rate: 1
            '''),
        )

        # Bad float
        self.assertRaises(
            Event.BadFloatException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - rate: not-a-float
            '''),
        )

        # Bad probability (negative)
        self.assertRaises(
            Event.BadProbabilityException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - probability: -0.1
            '''),
        )

        # Bad probability (too big)
        self.assertRaises(
            Event.BadProbabilityException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - probability: 2
            '''),
        )

        # Bad rate (negative)
        self.assertRaises(
            Event.BadRateException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - rate: -1
            '''),
        )

        # Bad rate (too big)
        self.assertRaises(
            Event.BadRateException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - rate: inf
            '''),
        )

        # Unrecognised key
        self.assertRaises(
            Event.UnrecognisedKeyException,
            FaultTree.build,
            textwrap.dedent('''
                Event: A
                - rate: 1
                - foo: bar
            '''),
        )

        # Quantity not set
        self.assertRaises(
            Event.QuantityNotSetException,
            FaultTree.build,
            'Event: A',
        )

    def test_fault_tree_build_gate(self):
        # Label already set
        self.assertRaises(
            Gate.LabelAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - label: First label
                - label: Second label
            '''),
        )

        # Type already set
        self.assertRaises(
            Gate.TypeAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - type: AND
                - type: AND
            '''),
        )

        # Inputs already set
        self.assertRaises(
            Gate.InputsAlreadySetException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - inputs: B, C
                - inputs: B, C
            '''),
        )

        # Bad type
        self.assertRaises(
            Gate.BadTypeException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - type: aNd
            '''),
        )

        # Missing inputs
        self.assertRaises(
            Gate.ZeroInputsException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - inputs: ,
            '''),
        )

        # Bad ID
        self.assertRaises(
            FaultTree.BadIdException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - inputs: good, (bad because of whitespace)
            '''),
        )

        # Unrecognised key
        self.assertRaises(
            Gate.UnrecognisedKeyException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - type: AND
                - foo: bar
            '''),
        )

        # Type not set
        self.assertRaises(
            Gate.TypeNotSetException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - inputs: B, C
            '''),
        )

        # Inputs not set
        self.assertRaises(
            Gate.InputsNotSetException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - type: OR
            '''),
        )

        # Unknown input
        self.assertRaises(
            Gate.UnknownInputException,
            FaultTree.build,
            textwrap.dedent('''
                Gate: A
                - type: OR
                - inputs: anonymous
            ''')
        )


if __name__ == '__main__':
    unittest.main()
