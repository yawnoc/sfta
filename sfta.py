#!/usr/bin/env python3

"""
# Slow Fault Tree Analyser (SFTA)

**Copyright 2022 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import argparse
import csv
import itertools
import os
import re
import sys
from math import prod as product


__version__ = '0.0.0'


def find_cycles(adjacency_dict):
    """
    Find cycles of a directed graph via three-state depth-first search.

    The three states are clean, infected, and dead.
    While clean nodes yet exist, a clean node is made infected.
    An infected node will:
    (1) if it has an infected child, have discovered a cycle;
    (2) make its clean children infected; and
    (3) become dead itself (having exhausted children to infect).
    """
    infection_cycles = set()
    infection_chain = []

    clean_nodes = set(adjacency_dict.keys())
    infected_nodes = set()
    dead_nodes = set()

    def infect(node):
        clean_nodes.discard(node)
        infected_nodes.add(node)
        infection_chain.append(node)

        for child_node in sorted(adjacency_dict[node]):
            if child_node in infected_nodes:
                child_index = infection_chain.index(child_node)
                infection_cycles.add(tuple(infection_chain[child_index:]))
            elif child_node in clean_nodes:
                infect(child_node)

        infection_chain.pop()
        infected_nodes.discard(node)
        dead_nodes.discard(node)

    while clean_nodes:
        first_clean_node = min(clean_nodes)
        infect(first_clean_node)

    return infection_cycles


class Writ:
    """
    Static class for performing calculations with writs.

    A __writ__ is an encoding of a cut set
    (i.e. a boolean term, a conjunction (AND) of events)
    by setting the nth bit if and only if the nth event is present as a factor.

    For example, if the events are A, B, C, D, E,
    then the writ for the cut set ABE is
        EDCBA
        10011 (binary),
    which is 19.

    Note that the writ 0 encodes an empty conjunction, which is True.
    """

    @staticmethod
    def to_writs(event_index):
        """
        Convert an event index to a set containing its corresponding writ.
        """
        return {1 << event_index}

    @staticmethod
    def to_event_indices(writ):
        """
        Convert a writ to a set containing the corresponding event indices.

        From <https://stackoverflow.com/a/49592515> (answer by Joe Samanek),
        the quickest way to extract the indices of set bits (from a writ)
        is to convert to a string and check for a match against '1'.
        The slice `[-1:1:-1]` means that the loop:
            -1: starts from the rightmost character (least significant bit)
             1: stops before '0b' prefix returned by `bin`
            -1: travels from right to left
        """
        return frozenset(
            index
            for index, digit in enumerate(bin(writ)[-1:1:-1])
            if digit == '1'
        )

    @staticmethod
    def and_(*input_writs):
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
    def or_(*input_writs):
        """
        Compute the OR (disjunction) of some input writs.

        Removes redundant writs as part of the computation.
        """
        undecided_writs = set(input_writs)
        disjunction_writs = set()

        while undecided_writs:
            writ = undecided_writs.pop()
            for other_writ in set(undecided_writs):
                if Writ.implieth(writ, other_writ):  # writ is redundant
                    break
                if Writ.implieth(other_writ, writ):  # other_writ is redundant
                    undecided_writs.discard(other_writ)
            else:  # writ is not redundant
                disjunction_writs.add(writ)

        return disjunction_writs

    @staticmethod
    def implieth(test_writ, reference_writ):
        """
        Decide whether a test writ implies a reference writ.

        Equivalent to deciding whether the term represented by the test writ
        is a multiple of the term represented by the reference writ.
        If so, the test term would be redundant in a disjunction (OR)
        with the reference term, as per the absorption law.

        The test writ will not imply the reference writ if and only if there is
        some bit not set in the test writ that is set in the reference writ.
        Hence we compute the bitwise AND between the test writ inverted
        and the reference writ, then compare unto zero.

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


class Tome:
    """
    A __tome__ holds a collection of writs (representing cut sets)
    and the quantity type (probability or rate).
    """
    def __init__(self, writs, quantity_type):
        self.writs = frozenset(writs)
        self.quantity_type = quantity_type

    def __eq__(self, other):
        return self.identity() == other.identity()

    def __hash__(self):
        return hash(self.identity())

    def identity(self):
        return self.writs, self.quantity_type

    @staticmethod
    def and_(*input_tomes):
        """
        Compute the AND (conjunction) of some input tomes.

        The first input may be a probability (initiator/enabler) or a rate
        (initiator). All subsequent inputs must be probabilities (enablers).
        Hence the conjunction has the same dimension as the first input.
        """
        non_first_rate_indices = [
            index
            for index, tome in enumerate(input_tomes)
            if index > 0 and tome.quantity_type == Event.TYPE_RATE
        ]
        if non_first_rate_indices:
            raise Tome.ConjunctionBadTypesException(non_first_rate_indices)

        conjunction_quantity_type = input_tomes[0].quantity_type

        writs_by_tome = (tome.writs for tome in input_tomes)
        writ_tuples_by_term = itertools.product(*writs_by_tome)
        conjunction_writs_by_term = (
            Writ.and_(*term_writ_tuple)
            for term_writ_tuple in writ_tuples_by_term
        )
        conjunction_writs = Writ.or_(*conjunction_writs_by_term)

        return Tome(conjunction_writs, conjunction_quantity_type)

    @staticmethod
    def or_(*input_tomes):
        """
        Compute the OR (disjunction) of some input tomes.

        All inputs must have the same dimension.
        """
        input_quantity_types = [
            tome.quantity_type for tome in input_tomes
        ]
        if len(set(input_quantity_types)) > 1:
            raise Tome.DisjunctionBadTypesException(input_quantity_types)

        disjunction_quantity_type = input_quantity_types[0]

        input_writs = (
            writ
            for tome in input_tomes
            for writ in tome.writs
        )
        disjunction_writs = Writ.or_(*input_writs)

        return Tome(disjunction_writs, disjunction_quantity_type)

    class ConjunctionBadTypesException(Exception):
        def __init__(self, non_first_rate_indices):
            self.non_first_rate_indices = non_first_rate_indices

    class DisjunctionBadTypesException(Exception):
        def __init__(self, input_quantity_types):
            self.input_quantity_types = input_quantity_types


class Event:
    def __init__(self, id_, index):
        self.id_ = id_
        self.index = index

        self.label = None
        self.label_line_number = None

        self.quantity_type = None
        self.quantity_value = None
        self.quantity_line_number = None

        self.tome = None

    KEY_EXPLAINER = (
        'Recognised keys for an Event property setting are:\n'
        '    label (optional)\n'
        '    probability or rate (exactly one required).'
    )

    TYPE_PROBABILITY = 0
    TYPE_RATE = 1

    STR_FROM_TYPE = {
        TYPE_PROBABILITY: 'probability',
        TYPE_RATE: 'rate',
    }

    @staticmethod
    def quantity_unit_str(quantity_type, time_unit):
        if quantity_type == Event.TYPE_PROBABILITY:
            return '1'

        if quantity_type == Event.TYPE_RATE:
            if time_unit is None:
                return '(unspecified)'
            else:
                return f'/{time_unit}'

        raise RuntimeError(
            'Implementation error: '
            '`quantity_type` is neither '
            '`Event.TYPE_PROBABILITY` nor `Event.TYPE_RATE`'
        )

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

    def compute_tome(self):
        self.tome = Tome(Writ.to_writs(self.index), self.quantity_type)

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
        self.label_line_number = None

        self.type = None
        self.type_line_number = None

        self.input_ids = None
        self.inputs_line_number = None

        self.tome = None

        self.cut_sets_indices = None
        self.quantity_type = None
        self.quantity_value_from_cut_set_indices = None
        self.quantity_value = None

    KEY_EXPLAINER = (
        'Recognised keys for a Gate property setting are:\n'
        '    label (optional)\n'
        '    type (required)\n'
        '    inputs (required).'
    )
    TYPE_EXPLAINER = 'Gate type must be either `AND` or `OR` (case-sensitive).'
    AND_INPUTS_EXPLAINER = (
        'The first input of an AND gate '
        'may be a probability (initiator/enabler) or a rate (initiator). '
        'All subsequent inputs must be probabilities (enablers).'
    )
    OR_INPUTS_EXPLAINER = (
        'OR gate inputs must be either all probabilities or all rates.'
    )

    TYPE_OR = 0
    TYPE_AND = 1

    STR_FROM_TYPE = {
        TYPE_OR: 'OR',
        TYPE_AND: 'AND',
    }

    @staticmethod
    def split_ids(input_ids_str):
        return list(filter(None, re.split(r'\s*,\s*', input_ids_str)))

    def set_label(self, label, line_number):
        if self.label is not None:
            raise Gate.LabelAlreadySetException(
                line_number,
                f'label hath already been set for Gate `{self.id_}` '
                f'at line {self.label_line_number}'
            )

        self.label = label
        self.label_line_number = line_number

    def set_type(self, type_str, line_number):
        if self.type is not None:
            raise Gate.TypeAlreadySetException(
                line_number,
                f'type hath already been set for Gate `{self.id_}` '
                f'at line {self.type_line_number}'
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
        self.type_line_number = line_number

    def set_inputs(self, input_ids_str, line_number):
        if self.input_ids is not None:
            raise Gate.InputsAlreadySetException(
                line_number,
                f'inputs have already been set for Gate `{self.id_}` '
                f'at line {self.inputs_line_number}'
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

    def compute_tome(self, event_from_id, gate_from_id):
        input_tomes = set()
        for input_id in self.input_ids:
            if input_id in event_from_id:  # input is Event
                event = event_from_id[input_id]
                input_tomes.add(event.tome)
            elif input_id in gate_from_id:  # input is Gate
                gate = gate_from_id[input_id]
                if gate.tome is None:
                    gate.compute_tome(event_from_id, gate_from_id)
                input_tomes.add(gate.tome)
            else:
                raise RuntimeError(
                    f'Implementation error: '
                    f'`{input_id}` is in '
                    f'neither `event_from_id` nor `gate_from_id`.'
                )

        if self.type == Gate.TYPE_AND:
            try:
                self.tome = Tome.and_(*input_tomes)
            except Tome.ConjunctionBadTypesException as exception:
                indices = exception.non_first_rate_indices
                ids = [self.input_ids[index] for index in indices]
                raise Gate.ConjunctionBadTypesException(
                    self.inputs_line_number,
                    f'non-first inputs of type rate for AND Gate `{self.id_}`:'
                    + '\n    '
                    + '\n    '.join(
                        f'`{id_}` (input #{index+1}) hath type rate'
                        for index, id_ in zip(indices, ids)
                    )
                    + f'\n\n{Gate.AND_INPUTS_EXPLAINER}'
                )
        elif self.type == Gate.TYPE_OR:
            try:
                self.tome = Tome.or_(*input_tomes)
            except Tome.DisjunctionBadTypesException as exception:
                type_strs = [
                    Event.STR_FROM_TYPE[type_]
                    for type_ in exception.input_quantity_types
                ]
                ids = self.input_ids
                raise Gate.DisjunctionBadTypesException(
                    self.inputs_line_number,
                    f'inputs of different type for OR Gate `{self.id_}`:'
                    + '\n    '
                    + '\n    '.join(
                        f'`{id_}` hath type {type_str}'
                        for id_, type_str in zip(ids, type_strs)
                    )
                    + f'\n\n{Gate.OR_INPUTS_EXPLAINER}'
                )
        else:
            raise RuntimeError(
                f'Implementation error: '
                f'Gate `type` is neither `TYPE_AND` nor `TYPE_OR`.'
            )

    def compute_quantity(self, quantity_value_from_event_index):
        self.cut_sets_indices = {
            Writ.to_event_indices(writ)
            for writ in self.tome.writs
        }
        self.quantity_type = self.tome.quantity_type
        self.quantity_value_from_cut_set_indices = {
            cut_set_indices:
                product(
                    quantity_value_from_event_index[event_index]
                    for event_index in cut_set_indices
                )
            for cut_set_indices in self.cut_sets_indices
        }
        self.quantity_value = (
            sum(self.quantity_value_from_cut_set_indices.values())
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

    class ConjunctionBadTypesException(FaultTreeTextException):
        pass

    class DisjunctionBadTypesException(FaultTreeTextException):
        pass


class FaultTree:
    def __init__(self, fault_tree_text):
        (
            self.events,
            self.gates,
            self.event_id_from_index,
            self.used_event_ids,
            self.top_gate_ids,
            self.time_unit,
        ) \
            = FaultTree.build(fault_tree_text)

    KEY_EXPLAINER = (
        'Recognised keys for a fault tree property setting are:\n'
        '    time_unit (optional).'
    )
    IDS_EXPLAINER = (
        'IDs may only contain letters, digits, underscores, and hyphens.'
    )
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

    @staticmethod
    def is_bad_id(string):
        return not re.fullmatch(r'[a-zA-Z0-9_-]+', string)

    @staticmethod
    def build(fault_tree_text):
        events, gates, time_unit = FaultTree.parse(fault_tree_text)
        event_id_from_index = {event.index: event.id_ for event in events}
        event_from_id = {event.id_: event for event in events}
        gate_from_id = {gate.id_: gate for gate in gates}

        used_event_ids, top_gate_ids = (
            FaultTree.validate_gate_inputs(event_from_id, gate_from_id)
        )
        FaultTree.validate_tree(gate_from_id)

        FaultTree.compute_event_tomes(events)
        FaultTree.compute_gate_tomes(event_from_id, gate_from_id)
        FaultTree.compute_gate_quantities(events, gates)

        return (
            events,
            gates,
            event_id_from_index,
            used_event_ids,
            top_gate_ids,
            time_unit,
        )

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

        return events, gates, time_unit

    @staticmethod
    def validate_gate_inputs(event_from_id, gate_from_id):
        event_ids = event_from_id.keys()
        gate_ids = gate_from_id.keys()
        gates = gate_from_id.values()

        used_event_ids = set()
        top_gate_ids = set(gate_ids)

        for gate in gates:
            for id_ in gate.input_ids:
                input_is_known_event = id_ in event_ids
                if input_is_known_event:
                    used_event_ids.add(id_)

                input_is_known_gate = id_ in gate_ids
                if input_is_known_gate:
                    top_gate_ids.discard(id_)

                if not (input_is_known_event or input_is_known_gate):
                    raise Gate.UnknownInputException(
                        gate.inputs_line_number,
                        f'no Event or Gate is ever declared with ID `{id_}`'
                    )

        return used_event_ids, top_gate_ids

    @staticmethod
    def validate_tree(gate_from_id):
        input_gate_ids_from_id = {
            id_: set(
                input_id
                for input_id in gate.input_ids
                if input_id in gate_from_id  # exclude Events
            )
            for id_, gate in gate_from_id.items()
        }

        cycles = find_cycles(input_gate_ids_from_id)
        if cycles:
            cycle = min(cycles)
            length = len(cycle)
            raise FaultTree.CircularGateInputsException(
                None,
                'circular gate inputs detected:'
                + '\n    '
                + '\n    '.join(
                    f'at line {gate_from_id[cycle[i]].inputs_line_number}: '
                    f'Gate `{cycle[i]}` hath input `{cycle[(i+1) % length]}`'
                    for i, _ in enumerate(cycle)
                )
            )

    @staticmethod
    def compute_event_tomes(events):
        for event in events:
            event.compute_tome()

    @staticmethod
    def compute_gate_tomes(event_from_id, gate_from_id):
        for gate in gate_from_id.values():
            gate.compute_tome(event_from_id, gate_from_id)

    @staticmethod
    def compute_gate_quantities(events, gates):
        quantity_value_from_event_index = {
            event.index: event.quantity_value
            for event in events
        }
        for gate in gates:
            gate.compute_quantity(quantity_value_from_event_index)

    def get_events_table(self):
        field_names = [
            'id',
            'is_used',
            'quantity_type',
            'quantity_value',
            'quantity_unit',
            'label',
        ]
        rows = [
            [
                event.id_,
                event.id_ in self.used_event_ids,
                Event.STR_FROM_TYPE[event.quantity_type],
                event.quantity_value,
                Event.quantity_unit_str(event.quantity_type, self.time_unit),
                event.label,
            ]
            for event in self.events
        ]
        rows.sort(key=lambda row: row[0])  # id
        return Table(field_names, rows)

    def get_gates_table(self):
        field_names = [
            'id',
            'is_top_gate',
            'quantity_type',
            'quantity_value',
            'quantity_unit',
            'type',
            'inputs',
            'label',
        ]
        rows = [
            [
                gate.id_,
                gate.id_ in self.top_gate_ids,
                Event.STR_FROM_TYPE[gate.quantity_type],
                gate.quantity_value,
                Event.quantity_unit_str(gate.quantity_type, self.time_unit),
                Gate.STR_FROM_TYPE[gate.type],
                ','.join(gate.input_ids),
                gate.label,
            ]
            for gate in self.gates
        ]
        rows.sort(key=lambda row: (-row[1], row[0]))  # is_top_gate, id
        return Table(field_names, rows)

    def get_cut_set_tables(self):
        cut_set_table_from_gate_id = {}
        for gate in self.gates:
            field_names = [
                'quantity_type',
                'quantity_value',
                'quantity_unit',
                'cut_set',
            ]
            rows = [
                [
                    Event.STR_FROM_TYPE[gate.quantity_type],
                    quantity_value,
                    Event.quantity_unit_str(
                        gate.quantity_type,
                        self.time_unit
                    ),
                    '.'.join(
                        self.event_id_from_index[event_index]
                        for event_index in cut_set_indices
                    ),
                ]
                for cut_set_indices, quantity_value
                in gate.quantity_value_from_cut_set_indices.items()
            ]
            rows.sort(key=lambda row: row[1])  # quantity_value
            cut_set_table_from_gate_id[gate.id_] = Table(field_names, rows)

        return cut_set_table_from_gate_id

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

    class CircularGateInputsException(FaultTreeTextException):
        pass


class Table:
    def __init__(self, field_names, rows):
        self.field_names = field_names
        self.rows = rows

    def write_tsv(self, file_name):
        with open(file_name, 'w', encoding='utf-8', newline='') as file:
            writer = (
                csv.writer(file, delimiter='\t', lineterminator=os.linesep)
            )
            writer.writerow(self.field_names)
            writer.writerows(self.rows)


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


def create_directory_robust(directory_name):
    if os.path.isfile(directory_name):
        os.remove(directory_name)
    if not os.path.isdir(directory_name):
        os.mkdir(directory_name)


def main():
    parsed_arguments = parse_command_line_arguments()
    text_file_name = parsed_arguments.fault_tree_text_file_name
    with open(text_file_name, 'r', encoding='utf-8') as file:
        fault_tree_text = file.read()

    try:
        fault_tree = FaultTree(fault_tree_text)
    except FaultTreeTextException as exception:
        line_number = exception.line_number
        message = exception.message

        if line_number:
            error_location_str = f'at line {line_number} '
        else:
            error_location_str = ''

        print(
            f'Error {error_location_str}in `{text_file_name}`:\n  {message}',
            file=sys.stderr,
        )
        sys.exit(1)

    events_table = fault_tree.get_events_table()
    gates_table = fault_tree.get_gates_table()
    cut_set_table_from_gate_id = fault_tree.get_cut_set_tables()

    output_directory_name = f'{text_file_name}.out'
    cut_sets_directory_name = f'{output_directory_name}/cut-sets'
    create_directory_robust(output_directory_name)
    create_directory_robust(cut_sets_directory_name)

    events_table.write_tsv(f'{output_directory_name}/events.tsv')
    gates_table.write_tsv(f'{output_directory_name}/gates.tsv')
    for gate_id, cut_set_table in cut_set_table_from_gate_id.items():
        cut_set_table.write_tsv(f'{cut_sets_directory_name}/{gate_id}.tsv')


if __name__ == '__main__':
    main()
