"""
# Slow Fault Tree Analyser: test_utilities.py

Unit tests for `utilities.py`.

**Copyright 2022–2024 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import unittest
from math import prod

from sfta.utilities import Nan
from sfta.utilities import blunt, dull, descending_product, descending_sum, find_cycles, escape_xml


class TestUtilities(unittest.TestCase):
    def test_blunt(self):
        self.assertEqual(blunt(None, 1), None)
        self.assertEqual(blunt(Nan, 1), 'nan')

        self.assertEqual(blunt(0, 1), '0')
        self.assertEqual(blunt(0., 1), '0')
        self.assertEqual(blunt(-0., 1), '0')

        self.assertNotEqual(str(0.1 + 0.2), '0.3')
        self.assertEqual(blunt(0.1 + 0.2, 1), '0.3')

        self.assertEqual(blunt(89640, 1), '89640')
        self.assertEqual(blunt(89640, 2), '89640')
        self.assertEqual(blunt(89640, 3), '89640')
        self.assertEqual(blunt(89640, 4), '89640')

        self.assertEqual(blunt(69.42069, 1), '69.4')
        self.assertEqual(blunt(69.42069, 2), '69.42')
        self.assertEqual(blunt(69.42069, 3), '69.421')
        self.assertEqual(blunt(69.42069, 4), '69.4207')
        self.assertEqual(blunt(69.42069, 5), '69.42069')
        self.assertEqual(blunt(69.42069, 6), '69.42069')

        self.assertEqual(blunt(0.00123456789, 1), '0')
        self.assertEqual(blunt(0.00123456789, 2), '0')
        self.assertEqual(blunt(0.00123456789, 3), '0.001')
        self.assertEqual(blunt(0.00123456789, 4), '0.0012')
        self.assertEqual(blunt(0.00123456789, 5), '0.00123')
        self.assertEqual(blunt(0.00123456789, 6), '0.001235')
        self.assertEqual(blunt(0.00123456789, 7), '0.0012346')
        self.assertEqual(blunt(0.00123456789, 8), '0.00123457')
        self.assertEqual(blunt(0.00123456789, 9), '0.001234568')
        self.assertEqual(blunt(0.00123456789, 10), '0.0012345679')
        self.assertEqual(blunt(0.00123456789, 11), '0.00123456789')
        self.assertEqual(blunt(0.00123456789, 12), '0.00123456789')

    def test_dull(self):
        self.assertEqual(dull(None), None)
        self.assertEqual(dull(Nan), 'nan')

        self.assertEqual(dull(0), '0')
        self.assertEqual(dull(0.), '0')
        self.assertEqual(dull(-0.), '0')

        self.assertEqual(dull(float('inf')), 'inf')
        self.assertEqual(dull(float('-inf')), '-inf')
        self.assertEqual(dull(float('nan')), 'nan')

        self.assertNotEqual(str(0.1 + 0.2), '0.3')
        self.assertEqual(dull(0.1 + 0.2, 1), '0.3')

        self.assertEqual(dull(89640, 1), '90000')
        self.assertEqual(dull(89640, 2), '90000')
        self.assertEqual(dull(89640, 3), '89600')
        self.assertEqual(dull(89640, 4), '89640')

        self.assertEqual(dull(69.42069, 1), '70')
        self.assertEqual(dull(69.42069, 2), '69')
        self.assertEqual(dull(69.42069, 3), '69.4')
        self.assertEqual(dull(69.42069, 4), '69.42')
        self.assertEqual(dull(69.42069, 5), '69.421')
        self.assertEqual(dull(69.42069, 6), '69.4207')
        self.assertEqual(dull(69.42069, 7), '69.42069')
        self.assertEqual(dull(69.42069, 8), '69.42069')

        self.assertEqual(dull(0.00123456789, 1), '1E-3')
        self.assertEqual(dull(0.00123456789, 2), '1.2E-3')
        self.assertEqual(dull(0.00123456789, 3), '1.23E-3')
        self.assertEqual(dull(0.00123456789, 4), '1.235E-3')
        self.assertEqual(dull(0.00123456789, 5), '1.2346E-3')
        self.assertEqual(dull(0.00123456789, 6), '1.23457E-3')
        self.assertEqual(dull(0.00123456789, 7), '1.234568E-3')
        self.assertEqual(dull(0.00123456789, 8), '1.2345679E-3')
        self.assertEqual(dull(0.00123456789, 9), '1.23456789E-3')
        self.assertEqual(dull(0.00123456789, 10), '1.23456789E-3')

        self.assertEqual(dull(1, coerce_scientific_exponent=1), '1')
        self.assertEqual(dull(0.1, coerce_scientific_exponent=1), '1E-1')
        self.assertEqual(dull(0.01, coerce_scientific_exponent=1), '1E-2')
        self.assertEqual(dull(0.001, coerce_scientific_exponent=1), '1E-3')

        self.assertEqual(dull(1, coerce_scientific_exponent=2), '1')
        self.assertEqual(dull(0.1, coerce_scientific_exponent=2), '0.1')
        self.assertEqual(dull(0.01, coerce_scientific_exponent=2), '1E-2')
        self.assertEqual(dull(0.001, coerce_scientific_exponent=2), '1E-3')

        self.assertEqual(dull(1, coerce_scientific_exponent=3), '1')
        self.assertEqual(dull(0.1, coerce_scientific_exponent=3), '0.1')
        self.assertEqual(dull(0.01, coerce_scientific_exponent=3), '0.01')
        self.assertEqual(dull(0.001, coerce_scientific_exponent=3), '1E-3')

    def test_descending_product(self):
        factors_1 = [0.1, 0.3, 0.5, 0.823]
        factors_2 = [0.823, 0.5, 0.3, 0.1]
        self.assertEqual(set(factors_1), set(factors_2))
        self.assertNotEqual(prod(factors_1), prod(factors_2))
        self.assertEqual(
            descending_product(factors_1),
            descending_product(factors_2),
        )

    def test_descending_sum(self):
        terms_1 = [1e-9, 2.5e-12, 5e-13, 5e-10, 2.5e-12]
        terms_2 = [1e-9, 5e-10, 2.5e-12, 2.5e-12, 5e-13]
        self.assertEqual(set(terms_1), set(terms_2))
        self.assertNotEqual(sum(terms_1), sum(terms_2))
        self.assertEqual(
            descending_sum(terms_1),
            descending_sum(terms_2),
        )

    def test_find_cycles(self):
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

    def test_escape_xml(self):
        self.assertEqual(escape_xml('&<>'), '&amp;&lt;&gt;')
        self.assertEqual(escape_xml('&amp;'), '&amp;')
        self.assertEqual(escape_xml('&&amp;'), '&amp;&amp;')
        self.assertEqual(escape_xml('&#1234567;'), '&#1234567;')
        self.assertEqual(escape_xml('&#12345678;'), '&amp;#12345678;')
        self.assertEqual(escape_xml('&#xABC123;'), '&#xABC123;')
        self.assertEqual(escape_xml('&#xABC123F;'), '&amp;#xABC123F;')


if __name__ == '__main__':
    unittest.main()
