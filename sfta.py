#!/usr/bin/env python3

"""
# Slow Fault Tree Analyser (SFTA)

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import argparse
import re


__version__ = '0.0.0'


class Writ:
    """
    Static class for performing calculations with writs.

    A __writ__ is an encoding of a boolean term (a conjunction of events)
    by setting the nth bit if and only if the nth event is present as a factor.

    For example, if the events are A, B, C, D, E,
    then the writ for the boolean term ABE is
        EDCBA
        10011 (binary),
    which is 19.

    Note that the writ 0 encodes an empty conjunction, which is True.
    """

    @staticmethod
    def conjunction(input_writs):
        """
        Compute the AND (conjunction) of some input writs.

        Since a factor is present in a conjunction
        if and only if it is present in at least one of the inputs,
        the conjunction writ is the bitwise OR of the input writs.

        For example:
            00000 | 00001 = 00001  <-->  True . A = A
            10011 | 00110 = 10111  <-->  ABE . BC = ABCE
        """
        conjunction_writ = 0
        for writ in input_writs:
            conjunction_writ |= writ

        return conjunction_writ

    @staticmethod
    def implies(test_writ, reference_writ):
        """
        Decide whether a test writ implies a reference writ.

        Equivalent to deciding whether the term represented by the test writ
        is a multiple of the term represented by the reference writ.
        If so, the test term would be redundant in a disjunction (OR)
        with the reference term, as per the absorption law.

        The test writ will not imply the reference writ if and only if there is
        some bit not set in the test writ that is set in the reference writ.
        Hence we compute the bitwise AND between the test writ negative
        and the reference writ, and then compare unto zero.

        For example:
             ~00100 & 00000 = 00000  <-->  C implies True
             ~00011 & 00001 = 00000  <-->  AB implies A
             ~11111 & 10011 = 00000  <-->  ABCDE implies ABE
             ~10000 & 00100 = 00100  <-->  E does not imply C (due to C)
             ~11001 & 00111 = 00110  <-->  ADE does not imply ABC (due to BC)
        """
        return ~test_writ & reference_writ == 0


class Event:
    def __init__(self, id_):
        self.id_ = id_


class Gate:
    def __init__(self, id_):
        self.id_ = id_


class FaultTree:
    def __init__(self, fault_tree_text):
        self.events, self.gates = FaultTree.parse(fault_tree_text)

    @staticmethod
    def is_bad_id(string):
        return re.search(r'[\s,.]', string)

    @staticmethod
    def parse(fault_tree_text):
        events = []
        gates = []

        current_object = None
        object_ids = set()

        for line_number, line in enumerate(fault_tree_text.splitlines(), 1):

            object_line_regex = r'^(?P<class_>Event|Gate): \s*(?P<id_>.+?)\s*$'
            object_line_match = re.match(object_line_regex, line)
            if object_line_match:
                class_ = object_line_match.group('class_')
                id_ = object_line_match.group('id_')

                if current_object is not None:
                    raise FaultTree.ObjectDeclarationException(line_number)
                if id_ in object_ids:
                    raise FaultTree.DuplicateIdException(line_number, id_)
                if FaultTree.is_bad_id(id_):
                    raise FaultTree.BadIdException(line_number, id_)

                if class_ == 'Event':
                    event = Event(id_)
                    events.append(event)
                    current_object = event
                elif class_ == 'Gate':
                    gate = Gate(id_)
                    gates.append(gate)
                    current_object = gate
                else:
                    raise RuntimeError(
                        f'Implementation error: '
                        f'`class_` matched from regex `{object_line_regex}` '
                        f'is neither `Event` nor `Gate`.'
                    )
                object_ids.add(id_)

                continue

            property_line_regex = r'^- (?P<key>[a-z]+): \s*(?P<value>.+?)\s*$'
            property_line_match = re.match(property_line_regex, line)
            if property_line_match:
                key = property_line_match.group('key')
                value = property_line_match.group('value')

                if current_object is None:
                    raise FaultTree.PropertyDeclarationException(line_number)

                if isinstance(current_object, Event):
                    pass  # TODO: Event property declaration
                elif isinstance(current_object, Gate):
                    pass  # TODO: Gate property declaration
                else:
                    raise RuntimeError(
                        f'Implementation error: '
                        f'current_object {current_object} '
                        f'is an instance of neither Event nor Gate.'
                    )

                continue

            if line == '':
                if current_object is None:
                    continue

                if isinstance(current_object, Event):
                    # TODO: Event object self-check
                    current_object = None
                elif isinstance(current_object, Gate):
                    # TODO: Gate object self-check
                    current_object = None
                else:
                    raise RuntimeError(
                        f'Implementation error: '
                        f'current_object {current_object} '
                        f'is an instance of neither Event nor Gate.'
                    )

                continue

            raise FaultTree.BadLineException(line_number)

        return events, gates

    class ObjectDeclarationException(Exception):
        def __init__(self, line_number):
            self.line_number = line_number

    class PropertyDeclarationException(Exception):
        def __init__(self, line_number):
            self.line_number = line_number

    class DuplicateIdException(Exception):
        def __init__(self, line_number, id_):
            self.line_number = line_number
            self.id_ = id_

    class BadIdException(Exception):
        def __init__(self, line_number, id_):
            self.line_number = line_number
            self.id_ = id_

    class BadLineException(Exception):
        def __init__(self, line_number):
            self.line_number = line_number


DESCRIPTION = 'Perform a slow fault tree analysis.'


def parse_command_line_arguments():
    argument_parser = argparse.ArgumentParser(description=DESCRIPTION)
    argument_parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'{argument_parser.prog} version {__version__}',
    )
    argument_parser.add_argument(
        'fault_tree_text_file_name',
        help='name of fault tree text file',
        metavar='ft.txt',
    )

    return argument_parser.parse_args()


def main():
    parsed_arguments = parse_command_line_arguments()
    file_name = parsed_arguments.fault_tree_text_file_name
    with open(file_name, 'r', encoding='utf-8') as file:
        fault_tree_text = file.read()

    fault_tree = FaultTree(fault_tree_text)


if __name__ == '__main__':
    main()
