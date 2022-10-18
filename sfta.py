"""
# Slow Fault Tree Analyser (SFTA)

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""


class Writ:
    """
    Static class providing methods for manipulating writs.

    A __writ__ is an encoding of a boolean term (a conjunction of events)
    by setting the nth bit if and only if the nth event is present as a factor.

    For example, if the events are A, B, C, D, E,
    then the writ for the boolean term ABE is
        EDCBA
        10011 (binary),
    which is 19.

    Note that the writ 0 encodes an empty conjunction, which is TRUE.
    """

    @staticmethod
    def conjunction(input_writs):
        """
        Compute the conjunction (logical AND) of input writs.

        Since a factor is present in a conjunction
        if and only if it is present in at least one of the inputs,
        the conjunction writ is the bitwise OR of the input writs.
        """
        conjunction_writ = 0
        for writ in input_writs:
            conjunction_writ |= writ

        return conjunction_writ
