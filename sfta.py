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
    def __init__(self, id_, index):
        self.id_ = id_
        self.index = index

        self.label = None
        self.label_line_number = None

        self.quantity_type = None
        self.quantity_value = None
        self.quantity_line_number = None

    KEY_EXPLAINER = (
        'Recognised keys for an Event property setting are:\n'
        '    label (optional)\n'
        '    probability or rate (exactly one required).'
    )

    TYPE_PROBABILITY = 0
    TYPE_RATE = 1

    def set_label(self, label, line_number):
        if self.label is not None:
            raise Event.LabelAlreadySetException(
                line_number,
                f'label hath already been set for Event `{self.id_}` '
                f'at line {self.label_line_number}'
            )

        self.label = label
        self.label_line_number = line_number

    def set_probability(self, probability_str, line_number):
        if self.quantity_type is not None:
            raise Event.QuantityAlreadySetException(
                line_number,
                f'probability or rate hath already been set '
                f'for Event `{self.id_}` '
                f'at line {self.quantity_line_number}'
            )

        try:
            probability = float(probability_str)
        except ValueError:
            raise Event.BadFloatException(
                line_number,
                f'unable to convert `{probability_str}` to float '
                f'for Event `{self.id_}`'
            )

        if probability < 0:
            raise Event.BadProbabilityException(
                line_number,
                f'probability `{probability_str}` is negative '
                f'for Event `{self.id_}`'
            )
        if probability > 1:
            raise Event.BadProbabilityException(
                line_number,
                f'probability `{probability_str}` exceedeth 1 '
                f'for Event `{self.id_}`'
            )

        self.quantity_type = Event.TYPE_PROBABILITY
        self.quantity_value = probability
        self.quantity_line_number = line_number

    def set_rate(self, rate_str, line_number):
        if self.quantity_type is not None:
            raise Event.QuantityAlreadySetException(
                line_number,
                f'probability or rate hath already been set '
                f'for Event `{self.id_}` '
                f'at line {self.quantity_line_number}'
            )

        try:
            rate = float(rate_str)
        except ValueError:
            raise Event.BadFloatException(
                line_number,
                f'unable to convert `{rate_str}` to float '
                f'for Event `{self.id_}`'
            )

        if rate < 0:
            raise Event.BadRateException(
                line_number,
                f'rate `{rate_str}` is negative for Event `{self.id_}`'
            )
        if not rate < float('inf'):
            raise Event.BadRateException(
                line_number,
                f'rate `{rate_str}` is not finite for Event `{self.id_}`'
            )

        self.quantity_type = Event.TYPE_RATE
        self.quantity_value = rate
        self.quantity_line_number = line_number

    def validate_properties(self, line_number):
        if self.quantity_type is None or self.quantity_value is None:
            raise Event.QuantityNotSetException(
                line_number,
                f'probability or rate hath not been set for Event `{self.id_}`'
            )

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
        self.inputs_line_number = None

    KEY_EXPLAINER = (
        'Recognised keys for a Gate property setting are:\n'
        '    label (optional)\n'
        '    type (required)\n'
        '    inputs (required).'
    )
    TYPE_EXPLAINER = 'Gate type must be either `AND` or `OR` (case-sensitive).'

    TYPE_OR = 0
    TYPE_AND = 1

    @staticmethod
    def split_ids(input_ids_str):
        return list(filter(None, re.split(r'\s*,\s*', input_ids_str)))

    def set_label(self, label, line_number):
        if self.label is not None:
            raise Gate.LabelAlreadySetException(
                line_number,
                f'label hath already been set for Gate `{self.id_}`'
            )

        self.label = label

    def set_type(self, type_str, line_number):
        if self.type is not None:
            raise Gate.TypeAlreadySetException(
                line_number,
                f'type hath already been set for Gate `{self.id_}`'
            )

        if type_str == 'OR':
            self.type = Gate.TYPE_OR
        elif type_str == 'AND':
            self.type = Gate.TYPE_AND
        else:
            raise Gate.BadTypeException(
                line_number,
                f'bad type `{type_str}` for Gate `{self.id_}`'
                f'\n\n{Gate.TYPE_EXPLAINER}'
            )

    def set_inputs(self, input_ids_str, line_number):
        if self.input_ids is not None:
            raise Gate.InputsAlreadySetException(
                line_number,
                f'inputs have already been set for Gate `{self.id_}`'
            )

        ids = Gate.split_ids(input_ids_str)
        if not ids:
            raise Gate.ZeroInputsException(
                line_number,
                f'no IDs could be extracted from inputs `{input_ids_str}` '
                f'for Gate `{self.id_}`'
            )
        for id_ in ids:
            if FaultTree.is_bad_id(id_):
                raise FaultTree.BadIdException(
                    line_number,
                    f'bad ID `{id_}` among inputs for Gate `{self.id_}`'
                    f'\n\n{FaultTree.IDS_EXPLAINER}'
                )

        self.input_ids = ids
        self.inputs_line_number = line_number

    def validate_properties(self, line_number):
        if self.type is None:
            raise Gate.TypeNotSetException(
                line_number,
                f'type hath not been set for Gate `{self.id_}`'
            )
        if self.input_ids is None:
            raise Gate.InputsNotSetException(
                line_number,
                f'inputs have not been set for Gate `{self.id_}`'
            )

    class LabelAlreadySetException(FaultTreeTextException):
        pass

    class TypeAlreadySetException(FaultTreeTextException):
        pass

    class InputsAlreadySetException(FaultTreeTextException):
        pass

    class BadTypeException(FaultTreeTextException):
        pass

    class ZeroInputsException(FaultTreeTextException):
        pass

    class UnrecognisedKeyException(FaultTreeTextException):
        pass

    class TypeNotSetException(FaultTreeTextException):
        pass

    class InputsNotSetException(FaultTreeTextException):
        pass

    class UnknownInputException(FaultTreeTextException):
        pass


class FaultTree:
    def __init__(self, fault_tree_text):
        self.event_from_id, self.gate_from_id, time_unit = (
            FaultTree.parse_and_validate(fault_tree_text)
        )

    IDS_EXPLAINER = 'IDs must not contain whitespace, commas, or full stops.'
    LINE_EXPLAINER = (
        'A line must have one of the following forms:\n'
        '    Event: <id>         (an Event declaration)\n'
        '    Gate: <id>          (a Gate declaration)\n'
        '    - <key>: <value>    (a property setting)\n'
        '    # <comment>         (a comment)\n'
        '    <a blank line>      (used before the next declaration).'
    )
    PROPERTY_EXPLAINER = (
        'Setting of properties for the fault tree itself '
        'must be done at the start of the file, '
        'even before any Event or Gate hath been declared.'
    )
    KEY_EXPLAINER = (
        'Recognised keys for a fault tree property setting are:\n'
        '    time_unit (optional).'
    )

    @staticmethod
    def is_bad_id(string):
        return re.search(r'[\s,.]', string)

    @staticmethod
    def parse_and_validate(fault_tree_text):
        event_from_id, gate_from_id, time_unit = (
            FaultTree.parse(fault_tree_text)
        )
        FaultTree.validate_gate_inputs(event_from_id, gate_from_id)
        # TODO: validate tree
        return event_from_id, gate_from_id, time_unit

    @staticmethod
    def parse(fault_tree_text):
        events = []
        gates = []
        time_unit = None

        event_index = 0
        current_object = FaultTree
        ids = set()

        lines = (fault_tree_text + '\n\n').splitlines()
        for line_number, line in enumerate(lines, 1):

            object_line_regex = r'^(?P<class_>Event|Gate): \s*(?P<id_>.+?)\s*$'
            object_line_match = re.match(object_line_regex, line)
            if object_line_match:
                class_ = object_line_match.group('class_')
                id_ = object_line_match.group('id_')

                if current_object not in (None, FaultTree):
                    raise FaultTree.SmotheredObjectDeclarationException(
                        line_number,
                        f'missing blank line before '
                        f'declaration of {class_} `{id_}`'
                    )
                if id_ in ids:
                    raise FaultTree.DuplicateIdException(
                        line_number,
                        f'duplicate ID `{id_}` in declaration of {class_}'
                    )
                if FaultTree.is_bad_id(id_):
                    raise FaultTree.BadIdException(
                        line_number,
                        f'bad ID `{id_}` in declaration of {class_}'
                        f'\n\n{FaultTree.IDS_EXPLAINER}'
                    )

                if class_ == 'Event':
                    event = Event(id_, event_index)
                    events.append(event)
                    event_index += 1
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
                ids.add(id_)
                continue

            property_line_regex = r'^- (?P<key>\S+): \s*(?P<value>.+?)\s*$'
            property_line_match = re.match(property_line_regex, line)
            if property_line_match:
                key = property_line_match.group('key')
                value = property_line_match.group('value')

                if current_object is None:
                    raise FaultTree.DanglingPropertySettingException(
                        line_number,
                        f'missing Event or Gate declaration before '
                        f'setting {key} to `{value}`'
                        f'\n\n{FaultTree.PROPERTY_EXPLAINER}'
                    )

                if current_object is FaultTree:
                    if key == 'time_unit':
                        time_unit = value
                    else:
                        raise FaultTree.UnrecognisedKeyException(
                            line_number,
                            f'unrecognised key `{key}` '
                            f'for the fault tree'
                            f'\n\n{FaultTree.KEY_EXPLAINER}'
                        )
                elif isinstance(current_object, Event):
                    if key == 'label':
                        current_object.set_label(value, line_number)
                    elif key == 'probability':
                        current_object.set_probability(value, line_number)
                    elif key == 'rate':
                        current_object.set_rate(value, line_number)
                    else:
                        raise Event.UnrecognisedKeyException(
                            line_number,
                            f'unrecognised key `{key}` '
                            f'for Event `{current_object.id_}`'
                            f'\n\n{Event.KEY_EXPLAINER}'
                        )
                elif isinstance(current_object, Gate):
                    if key == 'label':
                        current_object.set_label(value, line_number)
                    elif key == 'type':
                        current_object.set_type(value, line_number)
                    elif key == 'inputs':
                        current_object.set_inputs(value, line_number)
                    else:
                        raise Gate.UnrecognisedKeyException(
                            line_number,
                            f'unrecognised key `{key}` '
                            f'for Gate `{current_object.id_}`'
                            f'\n\n{Gate.KEY_EXPLAINER}'
                        )
                else:
                    raise RuntimeError(
                        f'Implementation error: '
                        f'current_object {current_object} '
                        f'is an instance of neither Event nor Gate.'
                    )
                continue

            comment_line_regex = '^#.*$'
            if re.match(comment_line_regex, line):
                continue

            blank_line_regex = r'^\s*$'
            if re.match(blank_line_regex, line):
                if current_object is None:
                    continue

                if current_object is FaultTree:
                    pass
                elif isinstance(current_object, (Event, Gate)):
                    current_object.validate_properties(line_number)
                    current_object = None
                else:
                    raise RuntimeError(
                        f'Implementation error: '
                        f'current_object {current_object} '
                        f'is an instance of neither Event nor Gate.'
                    )
                continue

            raise FaultTree.BadLineException(
                line_number,
                f'bad line `{line}`'
                f'\n\n{FaultTree.LINE_EXPLAINER}'
            )

        event_from_id = {event.id_: event for event in events}
        gate_from_id = {gate.id_: gate for gate in gates}

        return event_from_id, gate_from_id, time_unit

    @staticmethod
    def validate_gate_inputs(event_from_id, gate_from_id):
        event_ids = event_from_id.keys()
        gate_ids = gate_from_id.keys()
        gates = gate_from_id.values()

        for gate in gates:
            for id_ in gate.input_ids:
                if id_ not in event_ids and id_ not in gate_ids:
                    raise Gate.UnknownInputException(
                        gate.inputs_line_number,
                        f'no Event or Gate is ever declared with ID `{id_}`'
                    )

    class SmotheredObjectDeclarationException(FaultTreeTextException):
        pass

    class DanglingPropertySettingException(FaultTreeTextException):
        pass

    class DuplicateIdException(FaultTreeTextException):
        pass

    class BadIdException(FaultTreeTextException):
        pass

    class BadLineException(FaultTreeTextException):
        pass

    class UnrecognisedKeyException(FaultTreeTextException):
        pass


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

    try:
        fault_tree = FaultTree(fault_tree_text)
    except FaultTreeTextException as exception:
        line_number = exception.line_number
        message = exception.message
        print(
            f'Error at line {line_number} of `{file_name}`:\n  {message}',
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == '__main__':
    main()
