#!/usr/bin/env python3

"""
# Slow Fault Tree Analyser (SFTA)

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import argparse
import re
import sys


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


class FaultTreeTextException(Exception):
    def __init__(self, line_number, message):
        self.line_number = line_number
        self.message = message


class Event:
    def __init__(self, id_):
        self.id_ = id_
        self.label = None
        self.quantity_type = None
        self.quantity_value = None

    TYPE_PROBABILITY = 0
    TYPE_RATE = 1

    def set_label(self, label, line_number):
        if self.label is not None:
            message = f'label already set for Event `{self.id_}`'
            raise Event.LabelAlreadySetException(line_number, message)

        self.label = label

    def set_probability(self, probability_str, line_number):
        if self.quantity_type is not None:
            message = f'probability or rate already set for Event `{self.id_}`'
            raise Event.QuantityAlreadySetException(line_number, message)

        try:
            probability = float(probability_str)
        except ValueError:
            message = f'unable to convert `{probability_str}` to float'
            raise Event.BadFloatException(line_number, message)

        if probability < 0:
            message = f'probability `{probability_str}` is negative'
            raise Event.BadProbabilityException(line_number, message)
        if probability > 1:
            message = f'probability `{probability_str}` exceeds 1'
            raise Event.BadProbabilityException(line_number, message)

        self.quantity_type = Event.TYPE_PROBABILITY
        self.quantity_value = probability

    def set_rate(self, rate_str, line_number):
        if self.quantity_type is not None:
            message = f'probability or rate already set for Event `{self.id_}`'
            raise Event.QuantityAlreadySetException(line_number, message)

        try:
            rate = float(rate_str)
        except ValueError:
            message = f'unable to convert `{rate_str}` to float'
            raise Event.BadFloatException(line_number, message)

        if rate < 0:
            message = f'rate `{rate_str}` is negative'
            raise Event.BadRateException(line_number, message)
        if not rate < float('inf'):
            message = f'rate `{rate_str}` is not finite'
            raise Event.BadRateException(line_number, message)

        self.quantity_type = Event.TYPE_RATE
        self.quantity_value = rate

    def validate(self, line_number):
        if self.quantity_type is None or self.quantity_value is None:
            message = f'probability or rate not set for Event `{self.id_}`'
            raise Event.QuantityNotSetException(line_number, message)

    class LabelAlreadySetException(FaultTreeTextException):
        pass

    class QuantityAlreadySetException(FaultTreeTextException):
        pass

    class BadFloatException(FaultTreeTextException):
        pass

    class BadProbabilityException(FaultTreeTextException):
        pass

    class BadRateException(FaultTreeTextException):
        pass

    class UnrecognisedKeyException(FaultTreeTextException):
        pass

    class QuantityNotSetException(FaultTreeTextException):
        pass


class Gate:
    def __init__(self, id_):
        self.id_ = id_
        self.label = None
        self.type = None
        self.input_ids = None

    TYPE_OR = 0
    TYPE_AND = 1

    @staticmethod
    def split_ids(input_ids_str):
        return list(filter(None, re.split(r'\s*,\s*', input_ids_str)))

    def set_label(self, label, line_number):
        if self.label is not None:
            message = f'label already set for Gate `{self.id_}`'
            raise Gate.LabelAlreadySetException(line_number, message)

        self.label = label

    def set_type(self, type_str, line_number):
        if self.type is not None:
            message = f'type already set for Gate `{self.id_}`'
            raise Gate.TypeAlreadySetException(line_number, message)

        if type_str == 'OR':
            self.type = Gate.TYPE_OR
        elif type_str == 'AND':
            self.type = Gate.TYPE_AND
        else:
            message = f'type must be one of `OR`, `AND` (case-sensitive)'
            raise Gate.BadTypeException(line_number, message)

    def set_inputs(self, input_ids_str, line_number):
        if self.input_ids is not None:
            raise Gate.InputsAlreadySetException(line_number)

        ids = Gate.split_ids(input_ids_str)
        if not ids:
            raise Gate.MissingInputsException(line_number, input_ids_str)
        for id_ in ids:
            if FaultTree.is_bad_id(id_):
                raise FaultTree.BadIdException(line_number, id_)

        self.input_ids = ids

    def validate(self, line_number):
        if self.type is None:
            raise Gate.TypeNotSetException(line_number, self.id_)
        if self.input_ids is None:
            raise Gate.InputsNotSetException(line_number, self.id_)

    class LabelAlreadySetException(FaultTreeTextException):
        pass

    class TypeAlreadySetException(FaultTreeTextException):
        pass

    class InputsAlreadySetException(Exception):
        def __init__(self, line_number):
            self.line_number = line_number

    class BadTypeException(FaultTreeTextException):
        pass

    class MissingInputsException(Exception):
        def __init__(self, line_number, input_ids_str):
            self.line_number = line_number
            self.input_ids_str = input_ids_str

    class TypeNotSetException(Exception):
        def __init__(self, line_number, id_):
            self.line_number = line_number
            self.id_ = id_

    class InputsNotSetException(Exception):
        def __init__(self, line_number, id_):
            self.line_number = line_number
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

        lines = (fault_tree_text + '\n\n').splitlines()
        for line_number, line in enumerate(lines, 1):

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

            property_line_regex = r'^- (?P<key>\S+): \s*(?P<value>.+?)\s*$'
            property_line_match = re.match(property_line_regex, line)
            if property_line_match:
                key = property_line_match.group('key')
                value = property_line_match.group('value')

                if current_object is None:
                    raise FaultTree.PropertyDeclarationException(line_number)

                if isinstance(current_object, Event):
                    if key == 'label':
                        current_object.set_label(value, line_number)
                    elif key == 'probability':
                        current_object.set_probability(value, line_number)
                    elif key == 'rate':
                        current_object.set_rate(value, line_number)
                    else:
                        message = (
                            f'unrecognised key `{key}` '
                            f'for Event `{current_object.id_}`'
                        )
                        raise Event.UnrecognisedKeyException(
                            line_number,
                            message,
                        )
                elif isinstance(current_object, Gate):
                    if key == 'label':
                        current_object.set_label(value, line_number)
                    elif key == 'type':
                        current_object.set_type(value, line_number)
                    elif key == 'inputs':
                        current_object.set_inputs(value, line_number)
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

                if isinstance(current_object, (Event, Gate)):
                    current_object.validate(line_number)
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

    exception_classes = (
        Event.LabelAlreadySetException,
        Event.QuantityAlreadySetException,
        Event.BadFloatException,
        Event.BadProbabilityException,
        Event.BadRateException,
        Event.UnrecognisedKeyException,
        Event.QuantityNotSetException,
        Gate.LabelAlreadySetException,
        Gate.TypeAlreadySetException,
        Gate.BadTypeException,
    )
    try:
        fault_tree = FaultTree(fault_tree_text)
    except exception_classes as exception:
        line_number = exception.line_number
        message = exception.message
        print(
            f'Error at line {line_number} of `{file_name}`:\n  {message}',
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
