#!/usr/bin/env python3

"""
# test_sfta.py

Perform unit testing for `cmd.py`.

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import math
import textwrap
import unittest

from sfta import Event, FaultTree, Gate, Tome, Writ
from sfta import blunt, find_cycles


class TestSfta(unittest.TestCase):
    def test_blunt(self):
        self.assertEqual(blunt(None), None)

        self.assertEqual(blunt(0), 0)
        self.assertEqual(blunt(0.), 0)
        self.assertEqual(blunt(-0.), 0)

        self.assertEqual(blunt(float('inf')), float('inf'))
        self.assertEqual(blunt(float('-inf')), float('-inf'))
        self.assertTrue(math.isnan(blunt(float('nan'))))

        self.assertNotEqual(str(0.1 + 0.2), '0.3')
        self.assertEqual(blunt(0.1 + 0.2, 1), '0.3')

        self.assertEqual(blunt(69.42069, 1), '70')
        self.assertEqual(blunt(69.42069, 2), '69')
        self.assertEqual(blunt(69.42069, 3), '69.4')
        self.assertEqual(blunt(69.42069, 4), '69.42')
        self.assertEqual(blunt(69.42069, 5), '69.421')
        self.assertEqual(blunt(69.42069, 6), '69.4207')
        self.assertEqual(blunt(69.42069, 7), '69.42069')
        self.assertEqual(blunt(69.42069, 8), '69.42069')

        self.assertEqual(blunt(0.00123456789, 1), '0.001')
        self.assertEqual(blunt(0.00123456789, 2), '0.0012')
        self.assertEqual(blunt(0.00123456789, 3), '0.00123')
        self.assertEqual(blunt(0.00123456789, 4), '0.001235')
        self.assertEqual(blunt(0.00123456789, 5), '0.0012346')
        self.assertEqual(blunt(0.00123456789, 6), '0.00123457')
        self.assertEqual(blunt(0.00123456789, 7), '0.001234568')
        self.assertEqual(blunt(0.00123456789, 8), '0.0012345679')
        self.assertEqual(blunt(0.00123456789, 9), '0.00123456789')
        self.assertEqual(blunt(0.00123456789, 10), '0.00123456789')

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

    def test_writ_to_writs(self):
        self.assertEqual(Writ.to_writs(0), {2 ** 0})
        self.assertEqual(Writ.to_writs(1), {2 ** 1})
        self.assertEqual(Writ.to_writs(10), {2 ** 10})
        self.assertEqual(Writ.to_writs(69420), {2 ** 69420})

    def test_writ_to_event_indices(self):
        self.assertEqual(Writ.to_event_indices(0), set())
        self.assertEqual(Writ.to_event_indices(1), {0})
        self.assertEqual(Writ.to_event_indices(0b1010010), {1, 4, 6})
        self.assertEqual(Writ.to_event_indices(2 ** 69420), {69420})

    def test_writ_and(self):
        # (Empty conjunction) = True
        self.assertEqual(Writ.and_(), 0)

        # AC = AC
        self.assertEqual(Writ.and_(0b101), 0b101)

        # True . A = A
        self.assertEqual(Writ.and_(0, 1), 1)

        # ABE . BC = ABCE
        self.assertEqual(Writ.and_(0b10011, 0b00110), 0b10111)

        # C . A . B = ABC
        self.assertEqual(Writ.and_(0b100, 0b001, 0b010), 0b111)

        # ABCD . True . A = ABCD
        self.assertEqual(Writ.and_(0b1111, 0b0000, 0b0001), 0b1111)

    def test_writ_or(self):
        # (Empty disjunction) = False
        self.assertEqual(Writ.or_(), set())

        # A + True = True
        self.assertEqual(Writ.or_(1, 0), {0})

        # A + A + A = A
        self.assertEqual(Writ.or_(1, 1, 1), {1})

        # AC = AC
        self.assertEqual(Writ.or_(0b101), {0b101})

        # A + B + C = A + B + C
        self.assertEqual(Writ.or_(0b001, 0b010, 0b100), {0b001, 0b010, 0b100})

        # A + AB + BC = A + BC
        self.assertEqual(Writ.or_(0b001, 0b011, 0b110), {0b001, 0b110})

        # AB + BC + CA + ABC = AB + BC + CA
        self.assertEqual(
            Writ.or_(0b011, 0b110, 0b101, 0b111),
            {0b011, 0b110, 0b101},
        )

        # God save!
        self.assertEqual(
            Writ.or_(
                0b000011,  # AB
                0b000110,  # BC
                0b001100,  # CD
                0b010100,  # CE
                0b100000,  # F
                0b000111,  # ABC
                0b001011,  # ABD
                0b010011,  # ABE
                0b001101,  # ACD
                0b010101,  # ACE
                0b011001,  # ADE
                0b001110,  # BCD
                0b010110,  # BCE
                0b011010,  # BDE
                0b011100,  # CDE
                0b001111,  # ABCD
                0b010111,  # ABCE
                0b011011,  # ABDE
                0b011101,  # ACDE
                0b011110,  # BCDE
                0b110101,  # FACE
            ),
            {
                0b000011,  # AB
                0b000110,  # BC
                0b001100,  # CD
                0b010100,  # CE
                0b100000,  # F
                0b011001,  # ADE
                0b011010,  # BDE
            },
        )

    def test_writ_implieth(self):
        # A implies True
        self.assertTrue(Writ.implieth(1, 0))

        # AB implies A
        self.assertTrue(Writ.implieth(0b11, 0b01))

        # ABCDE implies ABE
        self.assertTrue(Writ.implieth(0b11111, 0b10011))

        # E does not imply C (due to C)
        self.assertFalse(Writ.implieth(0b10000, 0b00100))

        # ADE does not imply ABC (due to BC)
        self.assertFalse(Writ.implieth(0b11001, 0b00111))

    def test_tome_and(self):
        # True = True
        self.assertEqual(
            Tome.and_(Tome({0}, Event.TYPE_PROBABILITY)),
            Tome({0}, Event.TYPE_PROBABILITY),
        )

        # A . True = A
        self.assertEqual(
            Tome.and_(
                Tome({1}, Event.TYPE_PROBABILITY),
                Tome({0}, Event.TYPE_PROBABILITY),
            ),
            Tome({1}, Event.TYPE_PROBABILITY),
        )

        # A . B . C = ABC
        self.assertEqual(
            Tome.and_(
                Tome({0b001}, Event.TYPE_PROBABILITY),
                Tome({0b010}, Event.TYPE_PROBABILITY),
                Tome({0b100}, Event.TYPE_PROBABILITY),
            ),
            Tome({0b111}, Event.TYPE_PROBABILITY),
        )

        # A . AB . ABC = ABC
        self.assertEqual(
            Tome.and_(
                Tome({0b001}, Event.TYPE_PROBABILITY),
                Tome({0b011}, Event.TYPE_PROBABILITY),
                Tome({0b111}, Event.TYPE_PROBABILITY),
            ),
            Tome({0b111}, Event.TYPE_PROBABILITY),
        )

        # A . (A+B) = A
        self.assertEqual(
            Tome.and_(
                Tome({0b01}, Event.TYPE_PROBABILITY),
                Tome({0b01, 0b10}, Event.TYPE_PROBABILITY),
            ),
            Tome({0b01}, Event.TYPE_PROBABILITY),
        )

        # (A + B + E) . (A + B + C + D) = A + B + CE + DE
        self.assertEqual(
            Tome.and_(
                Tome(
                    {0b00001, 0b00010, 0b10000},
                    Event.TYPE_PROBABILITY,
                ),
                Tome(
                    {0b00001, 0b00010, 0b00100, 0b01000},
                    Event.TYPE_PROBABILITY,
                ),
            ),
            Tome(
                {0b00001, 0b00010, 0b10100, 0b11000},
                Event.TYPE_PROBABILITY,
            ),
        )

        # (A+B) . (A+C) . (A+D) . E = AE + BCDE
        self.assertEqual(
            Tome.and_(
                Tome({0b00001, 0b00010}, Event.TYPE_PROBABILITY),
                Tome({0b00001, 0b00100}, Event.TYPE_PROBABILITY),
                Tome({0b00001, 0b01000}, Event.TYPE_PROBABILITY),
                Tome({0b10000}, Event.TYPE_PROBABILITY),
            ),
            Tome(
                {0b10001, 0b11110},
                Event.TYPE_PROBABILITY,
            ),
        )

        # A (rate) . B (probability) . C (probability) = ABC (rate)
        self.assertEqual(
            Tome.and_(
                Tome({0b001}, Event.TYPE_RATE),
                Tome({0b010}, Event.TYPE_PROBABILITY),
                Tome({0b100}, Event.TYPE_PROBABILITY),
            ),
            Tome({0b111}, Event.TYPE_RATE),
        )

        # A (rate) . B (rate) is illegal
        self.assertRaises(
            Tome.ConjunctionBadTypesException,
            lambda events: Tome.and_(*events),
            [
                Tome({0b01}, Event.TYPE_RATE),
                Tome({0b10}, Event.TYPE_RATE),
            ],
        )

        # A (probability) . B (probability) . C (rate) is illegal
        self.assertRaises(
            Tome.ConjunctionBadTypesException,
            lambda events: Tome.and_(*events),
            [
                Tome({0b001}, Event.TYPE_PROBABILITY),
                Tome({0b010}, Event.TYPE_PROBABILITY),
                Tome({0b100}, Event.TYPE_RATE),
            ],
        )

    def test_tome_or(self):
        # A + True = True
        self.assertEqual(
            Tome.or_(
                Tome({1}, Event.TYPE_PROBABILITY),
                Tome({0}, Event.TYPE_PROBABILITY),
            ),
            Tome({0}, Event.TYPE_PROBABILITY),
        )

        # AB + BC + CA + ABC = AB + BC + CA
        self.assertEqual(
            Tome.or_(
                Tome({0b011}, Event.TYPE_PROBABILITY),
                Tome({0b110}, Event.TYPE_PROBABILITY),
                Tome({0b101}, Event.TYPE_PROBABILITY),
                Tome({0b111}, Event.TYPE_PROBABILITY),
            ),
            Tome({0b011, 0b110, 0b101}, Event.TYPE_PROBABILITY),
        )

        # A + A + B + C = A + B + C
        self.assertEqual(
            Tome.or_(
                Tome({0b001}, Event.TYPE_RATE),
                Tome({0b001}, Event.TYPE_RATE),
                Tome({0b010}, Event.TYPE_RATE),
                Tome({0b100}, Event.TYPE_RATE),
            ),
            Tome({0b001, 0b010, 0b100}, Event.TYPE_RATE),
        )

        # A (probability) + B (rate) is illegal
        self.assertRaises(
            Tome.DisjunctionBadTypesException,
            lambda events: Tome.or_(*events),
            [
                Tome({0b01}, Event.TYPE_PROBABILITY),
                Tome({0b10}, Event.TYPE_RATE),
            ],
        )

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
        self.assertTrue(FaultTree.is_bad_id('file/separators'))

        self.assertFalse(FaultTree.is_bad_id('abc123XYZ'))
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

        # AND gate with non-first rates
        self.assertRaises(
            Gate.ConjunctionBadTypesException,
            FaultTree.build,
            textwrap.dedent('''
                Event: P1
                - probability: 0.5

                Event: R2
                - rate: 2

                Event: P3
                - probability: 0.9

                Event: R4
                - rate: 4

                Gate: conjunction
                - type: AND
                - inputs: P1, R2, P3, R4
            '''),
        )

        # OR gate with different-typed input
        self.assertRaises(
            Gate.DisjunctionBadTypesException,
            FaultTree.build,
            textwrap.dedent('''
                Event: P
                - probability: 0.5

                Event: R
                - rate: 2

                Gate: P_R
                - type: OR
                - inputs: P, R
            '''),
        )


if __name__ == '__main__':
    unittest.main()
