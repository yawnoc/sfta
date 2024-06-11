"""
# Slow Fault Tree Analyser: core.py

Core (fault tree analysis) classes.

**Copyright 2022–2024 Conway**
Licensed under the GNU General Public License v3.0 (GPL-3.0-only).
This is free software with NO WARRANTY etc. etc., see LICENSE.
"""

import csv
import itertools
import os
import re
import textwrap
from math import sqrt

from sfta.utilities import descending_product, descending_sum, Nan, find_cycles, dull, blunt, escape_xml


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
             1: stops before the '0b' prefix returned by `bin`
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

        self.comment = None
        self.comment_line_number = None

        self.tome = None

    KEY_EXPLAINER = (
        'Recognised keys for an Event property setting are:\n'
        '    label (optional)\n'
        '    probability or rate (exactly one required)\n'
        '    comment (optional).'
    )

    TYPE_PROBABILITY = 0
    TYPE_RATE = 1

    STR_FROM_TYPE = {
        TYPE_PROBABILITY: 'probability',
        TYPE_RATE: 'rate',
    }

    @staticmethod
    def quantity_unit_str(quantity_type, time_unit, suppress_unity=False):
        if quantity_type == Event.TYPE_PROBABILITY:
            if suppress_unity:
                return ''
            else:
                return '1'

        if quantity_type == Event.TYPE_RATE:
            if time_unit is None:
                return '(unspecified)'
            else:
                return f'/{time_unit}'

        raise RuntimeError(
            'Implementation error: '
            '`quantity_type` is neither `TYPE_PROBABILITY` nor `TYPE_RATE`'
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

    def set_comment(self, comment, line_number):
        if self.comment is not None:
            raise Event.CommentAlreadySetException(
                line_number,
                f'comment hath already been set for Event `{self.id_}` '
                f'at line {self.comment_line_number}'
            )

        self.comment = comment
        self.comment_line_number = line_number

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

    class CommentAlreadySetException(FaultTreeTextException):
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

        self.is_paged = None
        self.is_paged_line_number = None

        self.type_ = None
        self.type_line_number = None

        self.input_ids = None
        self.inputs_line_number = None

        self.comment = None
        self.comment_line_number = None

        self.tome = None

        self.cut_sets_indices = None
        self.quantity_type = None
        self.quantity_value_from_cut_set_indices = None
        self.quantity_value = None

        self.contribution_value_from_event_index = None
        self.importance_from_event_index = None

    KEY_EXPLAINER = (
        'Recognised keys for a Gate property setting are:\n'
        '    label (optional)\n'
        '    is_paged (optional)\n'
        '    type (required)\n'
        '    inputs (required)\n'
        '    comment (optional).'
    )
    IS_PAGED_EXPLAINER = (
        'Gate is_paged must be either `True` or `False` (case-sensitive). '
        'The default value is `False`.'
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

    def set_is_paged(self, is_paged, line_number):
        if self.is_paged is not None:
            raise Gate.IsPagedAlreadySetException(
                line_number,
                f'is_paged hath already been set for `{self.id_}` '
                f'at line {self.is_paged_line_number}'
            )

        if is_paged not in ['True', 'False']:
            raise Gate.BadIsPagedException(
                line_number,
                f'bad is_paged `{is_paged}` for Gate `{self.id_}`'
                f'\n\n{Gate.IS_PAGED_EXPLAINER}'
            )
        self.is_paged = is_paged
        self.is_paged_line_number = line_number

    def set_type(self, type_str, line_number):
        if self.type_ is not None:
            raise Gate.TypeAlreadySetException(
                line_number,
                f'type hath already been set for Gate `{self.id_}` '
                f'at line {self.type_line_number}'
            )

        if type_str == 'OR':
            self.type_ = Gate.TYPE_OR
        elif type_str == 'AND':
            self.type_ = Gate.TYPE_AND
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

    def set_comment(self, comment, line_number):
        if self.comment is not None:
            raise Gate.CommentAlreadySetException(
                line_number,
                f'comment hath already been set for Gate `{self.id_}` '
                f'at line {self.comment_line_number}'
            )

        self.comment = comment
        self.comment_line_number = line_number

    def validate_properties(self, line_number):
        if self.is_paged is None:
            self.is_paged = False
        if self.type_ is None:
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
        input_tomes = []
        for input_id in self.input_ids:
            if input_id in event_from_id:  # input is Event
                event = event_from_id[input_id]
                input_tomes.append(event.tome)
            elif input_id in gate_from_id:  # input is Gate
                gate = gate_from_id[input_id]
                if gate.tome is None:
                    gate.compute_tome(event_from_id, gate_from_id)
                input_tomes.append(gate.tome)
            else:
                raise RuntimeError(
                    f'Implementation error: '
                    f'`{input_id}` is in '
                    f'neither `event_from_id` nor `gate_from_id`.'
                )

        if self.type_ == Gate.TYPE_AND:
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
        elif self.type_ == Gate.TYPE_OR:
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
                f'Gate `type_` is neither `TYPE_AND` nor `TYPE_OR`.'
            )

    def compute_quantity(self, quantity_value_from_event_index):
        self.cut_sets_indices = {
            Writ.to_event_indices(writ)
            for writ in self.tome.writs
        }
        self.quantity_type = self.tome.quantity_type
        self.quantity_value_from_cut_set_indices = {
            cut_set_indices:
                descending_product(
                    quantity_value_from_event_index[event_index]
                    for event_index in cut_set_indices
                )
            for cut_set_indices in self.cut_sets_indices
        }
        self.quantity_value = (
            descending_sum(self.quantity_value_from_cut_set_indices.values())
        )

    def compute_contributions(self, events):
        self.contribution_value_from_event_index = {
            event.index:
                descending_sum(
                    self.quantity_value_from_cut_set_indices[cut_set_indices]
                    for cut_set_indices in self.cut_sets_indices
                    if event.index in cut_set_indices
                )
            for event in events
        }
        self.importance_from_event_index = {
            event_index:
                Nan if self.quantity_value == 0
                else contribution_value / self.quantity_value
            for event_index, contribution_value
            in self.contribution_value_from_event_index.items()
        }

    class LabelAlreadySetException(FaultTreeTextException):
        pass

    class IsPagedAlreadySetException(FaultTreeTextException):
        pass

    class TypeAlreadySetException(FaultTreeTextException):
        pass

    class InputsAlreadySetException(FaultTreeTextException):
        pass

    class CommentAlreadySetException(FaultTreeTextException):
        pass

    class BadIsPagedException(FaultTreeTextException):
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
            self.event_from_id,
            self.gate_from_id,
            self.event_id_from_index,
            self.used_event_ids,
            self.top_gate_ids,
            self.time_unit,
        ) \
            = FaultTree.build(fault_tree_text)

    MAX_SIGNIFICANT_FIGURES = 4
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
        FaultTree.compute_gate_contributions(events, gates)

        return (
            event_from_id,
            gate_from_id,
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
        time_unit_line_number = None

        event_index = 0
        current_object = FaultTree
        ids = set()

        lines = (fault_tree_text + '\n\n').splitlines()
        for line_number, line in enumerate(lines, start=1):

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
                        if time_unit is not None:
                            raise FaultTree.TimeUnitAlreadySetException(
                                line_number,
                                f'time unit hath already been set '
                                f'at line {time_unit_line_number}'
                            )
                        time_unit = value
                        time_unit_line_number = line_number
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
                    elif key == 'comment':
                        current_object.set_comment(value, line_number)
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
                    elif key == 'is_paged':
                        current_object.set_is_paged(value, line_number)
                    elif key == 'type':
                        current_object.set_type(value, line_number)
                    elif key == 'inputs':
                        current_object.set_inputs(value, line_number)
                    elif key == 'comment':
                        current_object.set_comment(value, line_number)
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

    @staticmethod
    def compute_gate_contributions(events, gates):
        for gate in gates:
            gate.compute_contributions(events)

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
                id_,
                id_ in self.used_event_ids,
                Event.STR_FROM_TYPE[event.quantity_type],
                dull(event.quantity_value, FaultTree.MAX_SIGNIFICANT_FIGURES),
                Event.quantity_unit_str(event.quantity_type, self.time_unit),
                event.label,
            ]
            for id_, event in self.event_from_id.items()
        ]
        rows.sort(key=lambda row: row[0])  # id
        return Table(field_names, rows)

    def get_gates_table(self):
        field_names = [
            'id',
            'is_top_gate',
            'is_paged',
            'quantity_type',
            'quantity_value',
            'quantity_unit',
            'type',
            'inputs',
            'label',
        ]
        rows = [
            [
                id_,
                id_ in self.top_gate_ids,
                gate.is_paged,
                Event.STR_FROM_TYPE[gate.quantity_type],
                dull(gate.quantity_value, FaultTree.MAX_SIGNIFICANT_FIGURES),
                Event.quantity_unit_str(gate.quantity_type, self.time_unit),
                Gate.STR_FROM_TYPE[gate.type_],
                ','.join(gate.input_ids),
                gate.label,
            ]
            for id_, gate in self.gate_from_id.items()
        ]
        rows.sort(key=lambda row: (-row[1], row[0]))  # is_top_gate, id
        return Table(field_names, rows)

    def get_cut_set_tables(self):
        cut_set_table_from_gate_id = {}
        for gate_id, gate in self.gate_from_id.items():
            field_names = [
                'quantity_type',
                'quantity_value',
                'quantity_unit',
                'cut_set',
                'cut_set_order',
            ]
            rows = [
                [
                    Event.STR_FROM_TYPE[gate.quantity_type],
                    dull(quantity_value, FaultTree.MAX_SIGNIFICANT_FIGURES),
                    Event.quantity_unit_str(
                        gate.quantity_type,
                        self.time_unit,
                    ),
                    '.'.join(
                        self.event_id_from_index[event_index]
                        for event_index in sorted(cut_set_indices)
                    ),
                    len(cut_set_indices),
                ]
                for cut_set_indices, quantity_value
                in gate.quantity_value_from_cut_set_indices.items()
            ]
            rows.sort(
                key=lambda row: (-float(row[1]), row[4], row[3])
                # quantity_value, cut_set_order, cut_set
            )
            cut_set_table_from_gate_id[gate_id] = Table(field_names, rows)

        return cut_set_table_from_gate_id

    def get_contribution_tables(self):
        contribution_table_from_gate_id = {}
        for gate_id, gate in self.gate_from_id.items():
            field_names = [
                'event',
                'contribution_type',
                'contribution_value',
                'contribution_unit',
                'importance',
            ]
            rows = [
                [
                    event_id,
                    Event.STR_FROM_TYPE[gate.quantity_type],
                    dull(
                        gate.contribution_value_from_event_index[event_index],
                        FaultTree.MAX_SIGNIFICANT_FIGURES,
                    ),
                    Event.quantity_unit_str(
                        gate.quantity_type,
                        self.time_unit,
                    ),
                    dull(
                        gate.importance_from_event_index[event_index],
                        FaultTree.MAX_SIGNIFICANT_FIGURES,
                    )
                ]
                for event_index, event_id in self.event_id_from_index.items()
            ]
            rows.sort(
                key=lambda row: (-float(row[2]), row[0])
                # contribution_value, event
            )
            contribution_table_from_gate_id[gate_id] = Table(field_names, rows)

        return contribution_table_from_gate_id

    def get_figures(self):
        figure_from_id = {
            id_: Figure(self, id_)
            for id_, gate in self.gate_from_id.items()
            if id_ in self.top_gate_ids or gate.is_paged
        }
        return figure_from_id

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

    class TimeUnitAlreadySetException(FaultTreeTextException):
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


class Figure:
    MARGIN = 10

    def __init__(self, fault_tree, id_):
        event_from_id = fault_tree.event_from_id
        gate_from_id = fault_tree.gate_from_id
        time_unit = fault_tree.time_unit

        top_node = (
            Node(event_from_id, gate_from_id, time_unit, id_, to_node=None)
        )
        top_node.position_recursive()

        self.top_node = top_node
        self.occurrence_ids = {
            implicated_id
            for implicated_id in top_node.implicated_ids
            if implicated_id != id_
        }

    def get_svg_content(self):
        top_node = self.top_node

        left = -Figure.MARGIN
        top = -Figure.MARGIN
        width = top_node.width + 2 * Figure.MARGIN
        height = top_node.height + 2 * Figure.MARGIN

        xmlns = 'http://www.w3.org/2000/svg'
        font_size = Node.DEFAULT_FONT_SIZE
        elements = top_node.get_svg_elements_recursive()

        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg viewBox="{left} {top} {width} {height}" xmlns="{xmlns}">\n'
            f'<style>\n'
            f'circle, path, polygon, rect {{\n'
            f'  fill: lightyellow;\n'
            f'}}\n'
            f'circle, path, polygon, polyline, rect {{\n'
            f'  stroke: black;\n'
            f'  stroke-width: 1.3;\n'
            f'}}\n'
            f'polyline {{\n'
            f'  fill: none;\n'
            f'}}\n'
            f'text {{\n'
            f'  dominant-baseline: middle;\n'
            f'  font-family: Consolas, Cousine, "Courier New", monospace;\n'
            f'  font-size: {font_size}px;\n'
            f'  text-anchor: middle;\n'
            f'}}\n'
            f'</style>\n'
            f'{elements}\n'
            f'</svg>\n'
        )

    def write_svg(self, file_name):
        svg_content = self.get_svg_content()
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(svg_content)


class Node:
    """
    A node which instantiates recursively, of a figure.
    """
    SYMBOL_TYPE_NULL = -1
    SYMBOL_TYPE_OR = 0
    SYMBOL_TYPE_AND = 1
    SYMBOL_TYPE_EVENT = 2
    SYMBOL_TYPE_PAGED = 3

    WIDTH = 120
    HEIGHT = 210
    DEFAULT_FONT_SIZE = 10
    LINE_SPACING = 1.3

    LABEL_BOX_Y_OFFSET = -65
    LABEL_BOX_WIDTH = 108
    LABEL_BOX_HEIGHT = 70
    LABEL_BOX_TARGET_RATIO = 5.4  # line length divided by line count
    LABEL_MIN_LINE_LENGTH = 16

    ID_BOX_Y_OFFSET = -13
    ID_BOX_WIDTH = 108
    ID_BOX_HEIGHT = 24

    SYMBOL_Y_OFFSET = 45
    SYMBOL_SLOTS_HALF_WIDTH = 30

    CONNECTOR_BUS_Y_OFFSET = 95
    CONNECTOR_BUS_HALF_HEIGHT = 10

    OR_APEX_HEIGHT = 38  # tip, above centre
    OR_NECK_HEIGHT = -10  # ears, above centre
    OR_BODY_HEIGHT = 36  # toes, below centre
    OR_SLANT_DROP = 2  # control points, below apex
    OR_SLANT_RUN = 6  # control points, beside apex
    OR_SLING_RISE = 35  # control points, above toes
    OR_GROIN_RISE = 30  # control point, between toes
    OR_HALF_WIDTH = 33

    AND_NECK_HEIGHT = 6  # ears, above centre
    AND_BODY_HEIGHT = 34  # toes, below centre
    AND_SLING_RISE = 42  # control points, above toes
    AND_HALF_WIDTH = 32

    EVENT_CIRCLE_RADIUS = 38

    PAGED_APEX_HEIGHT = 36  # tip, above centre
    PAGED_BODY_HEIGHT = 32  # toes, below centre
    PAGED_HALF_WIDTH = 40

    QUANTITY_BOX_Y_OFFSET = 45
    QUANTITY_BOX_WIDTH = 108
    QUANTITY_BOX_HEIGHT = 24

    def __init__(self, event_from_id, gate_from_id, time_unit, id_, to_node):
        if id_ in event_from_id.keys():  # object is Event
            reference_object = event_from_id[id_]
            symbol_type = Node.SYMBOL_TYPE_EVENT
            input_nodes = []
        elif id_ in gate_from_id.keys():  # object is Gate
            reference_object = gate = gate_from_id[id_]
            if gate.is_paged and to_node is not None:
                input_ids = []
                symbol_type = Node.SYMBOL_TYPE_PAGED
            else:
                input_ids = gate.input_ids
                if len(input_ids) == 1:
                    symbol_type = Node.SYMBOL_TYPE_NULL
                elif gate.type_ == Gate.TYPE_OR:
                    symbol_type = Node.SYMBOL_TYPE_OR
                elif gate.type_ == Gate.TYPE_AND:
                    symbol_type = Node.SYMBOL_TYPE_AND
                else:
                    raise RuntimeError(
                        f'Implementation error: '
                        f'Gate `type_` is neither `TYPE_AND` nor `TYPE_OR`.'
                    )
            input_nodes = [
                Node(
                    event_from_id,
                    gate_from_id,
                    time_unit,
                    input_id,
                    to_node=self,
                )
                for input_id in input_ids
            ]
        else:
            raise RuntimeError(
                f'Implementation error: '
                f'`{id_}` is in '
                f'neither `event_from_id` nor `gate_from_id`.'
            )

        implicated_ids = {
            id_,
            *{
                id_
                for node in input_nodes
                for id_ in node.implicated_ids
            },
        }

        if input_nodes:
            width = sum(node.width for node in input_nodes)
            height = Node.HEIGHT + max(node.height for node in input_nodes)
        else:
            width = Node.WIDTH
            height = Node.HEIGHT

        self.to_node = to_node
        self.reference_object = reference_object
        self.symbol_type = symbol_type
        self.time_unit = time_unit
        self.input_nodes = input_nodes
        self.implicated_ids = implicated_ids
        self.width = width
        self.height = height

        self.x = None
        self.y = None

    def position_recursive(self):
        to_node = self.to_node
        if to_node is None:
            self.x = self.width // 2
            self.y = Node.HEIGHT // 2
        else:
            to_node_inputs = to_node.input_nodes
            input_index = to_node_inputs.index(self)
            nodes_before = to_node_inputs[0:input_index]
            width_before = sum(node.width for node in nodes_before)
            x_offset = -to_node.width // 2 + width_before + self.width // 2
            self.x = to_node.x + x_offset
            self.y = to_node.y + Node.HEIGHT

        for input_node in self.input_nodes:
            input_node.position_recursive()

    def get_svg_elements_recursive(self):
        x = self.x
        y = self.y
        input_nodes = self.input_nodes
        symbol_type = self.symbol_type
        time_unit = self.time_unit

        reference_object = self.reference_object
        id_ = reference_object.id_
        label = reference_object.label
        quantity_value = reference_object.quantity_value
        quantity_type = reference_object.quantity_type
        hath_multiple_writs = len(reference_object.tome.writs) > 1

        self_elements = [
            Node.label_symbol_connector_element(x, y),
            Node.symbol_input_connector_elements(input_nodes, x, y),
            Node.label_rectangle_element(x, y),
            Node.label_text_elements(x, y, label),
            Node.id_rectangle_element(x, y),
            Node.id_text_element(x, y, id_),
            Node.symbol_element(x, y, symbol_type),
            Node.quantity_rectangle_element(x, y),
            Node.quantity_text_element(
                x, y,
                quantity_value, quantity_type, hath_multiple_writs,
                time_unit,
            ),
        ]
        input_elements = [
            input_node.get_svg_elements_recursive()
            for input_node in self.input_nodes
        ]

        return '\n'.join(self_elements + input_elements)

    @staticmethod
    def label_symbol_connector_element(x, y):
        centre = x
        label_middle = y - Node.LABEL_BOX_HEIGHT // 2 + Node.LABEL_BOX_Y_OFFSET
        symbol_middle = y + Node.SYMBOL_Y_OFFSET

        points = f'{centre},{label_middle} {centre},{symbol_middle}'

        return f'<polyline points="{points}"/>'

    @staticmethod
    def symbol_input_connector_elements(input_nodes, x, y):
        if not input_nodes:
            return ''

        symbol_centre = x
        symbol_middle = y + Node.SYMBOL_Y_OFFSET
        bus_middle = y + Node.CONNECTOR_BUS_Y_OFFSET

        input_numbers_left = []
        input_numbers_right = []
        for input_number, input_node in enumerate(input_nodes, start=1):
            input_node_centre = input_node.x
            if input_node_centre < symbol_centre:
                input_numbers_left.append(input_number)
            elif input_node_centre > symbol_centre:
                input_numbers_right.append(input_number)

        input_count = len(input_nodes)
        left_input_count = len(input_numbers_left)
        right_input_count = len(input_numbers_right)

        points_by_input = []
        for input_number, input_node in enumerate(input_nodes, start=1):
            slot_bias = 2 * input_number / (1 + input_count) - 1
            slot_x = round(
                symbol_centre + slot_bias * Node.SYMBOL_SLOTS_HALF_WIDTH
            )

            if input_number in input_numbers_left:
                left_number = input_numbers_left.index(input_number) + 1
                bus_bias = 2 * left_number / (1 + left_input_count) - 1
            elif input_number in input_numbers_right:
                right_number = input_numbers_right.index(input_number) + 1
                bus_bias = 1 - 2 * right_number / (1 + right_input_count)
            else:
                bus_bias = 0
            bus_y = round(
                bus_middle + bus_bias * Node.CONNECTOR_BUS_HALF_HEIGHT
            )

            input_label_centre = input_node.x
            input_label_middle = input_node.y + Node.LABEL_BOX_Y_OFFSET

            points_by_input.append(
                ' '.join([
                    f'{slot_x},{symbol_middle}',
                    f'{slot_x},{bus_y}',
                    f'{input_label_centre},{bus_y}',
                    f'{input_label_centre},{input_label_middle}',
                ])
            )

        return '\n'.join(
            f'<polyline points="{points}"/>'
            for points in points_by_input
        )

    @staticmethod
    def label_rectangle_element(x, y):
        left = x - Node.LABEL_BOX_WIDTH // 2
        top = y - Node.LABEL_BOX_HEIGHT // 2 + Node.LABEL_BOX_Y_OFFSET
        width = Node.LABEL_BOX_WIDTH
        height = Node.LABEL_BOX_HEIGHT

        return (
            f'<rect x="{left}" y="{top}" width="{width}" height="{height}"/>'
        )

    @staticmethod
    def label_text_elements(x, y, label):
        if label is None:
            return ''

        centre = x
        middle = y + Node.LABEL_BOX_Y_OFFSET

        target_line_length = max(
            Node.LABEL_MIN_LINE_LENGTH,
            round(sqrt(Node.LABEL_BOX_TARGET_RATIO * len(label))),
        )
        lines = textwrap.wrap(label, target_line_length)

        max_line_length = max(len(line) for line in lines)
        scale_factor = min(
            1.,
            Node.LABEL_MIN_LINE_LENGTH / max_line_length,
        )
        font_size = scale_factor * Node.DEFAULT_FONT_SIZE
        font_size_str = blunt(font_size, max_decimal_places=1)
        style = f'font-size: {font_size_str}px'

        line_count = len(lines)
        text_elements = []
        for line_number, line in enumerate(lines, start=1):
            bias = line_number - (1 + line_count) / 2
            line_middle = blunt(
                middle + bias * font_size * Node.LINE_SPACING,
                max_decimal_places=1,
            )
            content = escape_xml(line)

            text_elements.append(
                f'<text'
                f' x="{centre}"'
                f' y="{line_middle}"'
                f' style="{style}"'
                f'>{content}</text>'
            )

        return '\n'.join(text_elements)

    @staticmethod
    def id_rectangle_element(x, y):
        left = x - Node.ID_BOX_WIDTH // 2
        top = y - Node.ID_BOX_HEIGHT // 2 + Node.ID_BOX_Y_OFFSET
        width = Node.ID_BOX_WIDTH
        height = Node.ID_BOX_HEIGHT

        return (
            f'<rect x="{left}" y="{top}" width="{width}" height="{height}"/>'
        )

    @staticmethod
    def id_text_element(x, y, id_):
        centre = x
        middle = y + Node.ID_BOX_Y_OFFSET
        content = escape_xml(id_)

        return f'<text x="{centre}" y="{middle}">{content}</text>'

    @staticmethod
    def symbol_element(x, y, symbol_type):
        if symbol_type == Node.SYMBOL_TYPE_OR:
            return Node.or_symbol_element(x, y)

        if symbol_type == Node.SYMBOL_TYPE_AND:
            return Node.and_symbol_element(x, y)

        if symbol_type == Node.SYMBOL_TYPE_EVENT:
            return Node.event_symbol_element(x, y)

        if symbol_type == Node.SYMBOL_TYPE_PAGED:
            return Node.paged_symbol_element(x, y)

        return ''

    @staticmethod
    def or_symbol_element(x, y):
        apex_x = x
        apex_y = y - Node.OR_APEX_HEIGHT + Node.SYMBOL_Y_OFFSET

        left_x = x - Node.OR_HALF_WIDTH
        right_x = x + Node.OR_HALF_WIDTH

        ear_y = y - Node.OR_NECK_HEIGHT + Node.SYMBOL_Y_OFFSET
        toe_y = y + Node.OR_BODY_HEIGHT + Node.SYMBOL_Y_OFFSET

        left_slant_x = apex_x - Node.OR_SLANT_RUN
        right_slant_x = apex_x + Node.OR_SLANT_RUN
        slant_y = apex_y + Node.OR_SLANT_DROP

        sling_y = ear_y - Node.OR_SLING_RISE

        groin_x = x
        groin_y = toe_y - Node.OR_GROIN_RISE

        commands = (
            f'M{apex_x},{apex_y} '
            f'C{left_slant_x},{slant_y} {left_x},{sling_y} {left_x},{ear_y} '
            f'L{left_x},{toe_y} '
            f'Q{groin_x},{groin_y} {right_x},{toe_y} '
            f'L{right_x},{ear_y} '
            f'C{right_x},{sling_y} {right_slant_x},{slant_y} {apex_x},{apex_y}'
        )

        return f'<path d="{commands}"/>'

    @staticmethod
    def and_symbol_element(x, y):
        left_x = x - Node.AND_HALF_WIDTH
        right_x = x + Node.AND_HALF_WIDTH

        ear_y = y - Node.AND_NECK_HEIGHT + Node.SYMBOL_Y_OFFSET
        toe_y = y + Node.AND_BODY_HEIGHT + Node.SYMBOL_Y_OFFSET

        sling_y = ear_y - Node.AND_SLING_RISE

        commands = (
            f'M{left_x},{toe_y} '
            f'L{right_x},{toe_y} '
            f'L{right_x},{ear_y} '
            f'C{right_x},{sling_y} {left_x},{sling_y} {left_x},{ear_y} '
            f'L{left_x},{toe_y} '
        )

        return f'<path d="{commands}"/>'

    @staticmethod
    def event_symbol_element(x, y):
        centre = x
        middle = y + Node.SYMBOL_Y_OFFSET
        radius = Node.EVENT_CIRCLE_RADIUS

        return f'<circle cx="{centre}" cy="{middle}" r="{radius}"/>'

    @staticmethod
    def paged_symbol_element(x, y):
        apex_x = x
        apex_y = y - Node.PAGED_APEX_HEIGHT + Node.SYMBOL_Y_OFFSET

        left_x = x - Node.PAGED_HALF_WIDTH
        right_x = x + Node.PAGED_HALF_WIDTH
        toe_y = y + Node.PAGED_BODY_HEIGHT + Node.SYMBOL_Y_OFFSET

        points = f'{apex_x},{apex_y} {left_x},{toe_y} {right_x},{toe_y}'

        return f'<polygon points="{points}"/>'

    @staticmethod
    def quantity_rectangle_element(x, y):
        left = x - Node.QUANTITY_BOX_WIDTH // 2
        top = y - Node.QUANTITY_BOX_HEIGHT // 2 + Node.QUANTITY_BOX_Y_OFFSET
        width = Node.QUANTITY_BOX_WIDTH
        height = Node.QUANTITY_BOX_HEIGHT

        return (
            f'<rect x="{left}" y="{top}" width="{width}" height="{height}"/>'
        )

    @staticmethod
    def quantity_text_element(
        x, y,
        quantity_value, quantity_type, hath_multiple_writs,
        time_unit,
    ):
        centre = x
        middle = y + Node.QUANTITY_BOX_Y_OFFSET

        if quantity_type == Event.TYPE_PROBABILITY:
            lhs = 'Q'
        elif quantity_type == Event.TYPE_RATE:
            lhs = 'w'
        else:
            raise RuntimeError(
                'Implementation error: '
                '`quantity_type` is neither `TYPE_PROBABILITY` nor `TYPE_RATE`'
            )

        if hath_multiple_writs:
            relation = '≤'
        else:
            relation = '='

        value_str = dull(quantity_value, FaultTree.MAX_SIGNIFICANT_FIGURES)
        unit_str = Event.quantity_unit_str(
            quantity_type,
            time_unit,
            suppress_unity=True,
        )

        content = escape_xml(f'{lhs} {relation} {value_str}{unit_str}')

        return f'<text x="{centre}" y="{middle}">{content}</text>'


class Index:
    """
    A two-way index between figures and their objects.
    """
    def __init__(self, figure_from_id, figures_directory_name):
        ids_from_figure_id = {}
        figure_ids_from_id = {}

        for figure_id, figure in figure_from_id.items():
            ids_from_figure_id[figure_id] = figure.occurrence_ids
            for id_ in figure.occurrence_ids:
                figure_ids_from_id.setdefault(id_, set()).add(figure_id)

        self.ids_from_figure_id = ids_from_figure_id
        self.figure_ids_from_id = figure_ids_from_id
        self.figures_directory_name = figures_directory_name

    def get_html_content(self):
        figures_directory_name = escape_xml(self.figures_directory_name)

        meta_charset = '<meta charset="utf-8">'
        meta_viewport = (
            '<meta'
            ' name="viewport"'
            ' content="width=device-width, initial-scale=1"'
            '>'
        )
        title = f'Index of `{figures_directory_name}/`'
        heading = f'Index of <code>{figures_directory_name}/</code>'

        object_lookup_table_html = self.get_object_lookup_table_html()
        figure_lookup_table_html = self.get_figure_lookup_table_html()

        return (
            f'<!DOCTYPE html>\n'
            f'<html lang="en">\n'
            f'<head>\n'
            f'  {meta_charset}\n'
            f'  {meta_viewport}\n'
            f'  <title>{title}</title>\n'
            f'  <style>\n'
            f'    html {{\n'
            f'      margin: 0 auto;\n'
            f'      max-width: 45em;\n'
            f'    }}\n'
            f'    table {{\n'
            f'      border-spacing: 0;\n'
            f'      border-collapse: collapse;\n'
            f'      margin-top: 0.5em;\n'
            f'      margin-bottom: 1em;\n'
            f'    }}\n'
            f'    th {{\n'
            f'      background-clip: padding-box;\n'
            f'      background-color: lightgrey;\n'
            f'      position: sticky;\n'
            f'      top: 0;\n'
            f'    }}\n'
            f'    th, td {{\n'
            f'      border: 1px solid black;\n'
            f'      padding: 0.4em;\n'
            f'    }}\n'
            f'  </style>\n'
            f'</head>\n'
            f'<body>\n'
            f'<h1>{heading}</h1>\n'
            f'<h2>Lookup by object</h2>'
            f'{object_lookup_table_html}'
            f'<h2>Lookup by figure</h2>'
            f'{figure_lookup_table_html}'
            f'</body>\n'
            f'</html>\n'
        )

    def get_object_lookup_table_html(self):
        figure_ids_from_id = self.figure_ids_from_id

        tbody_rows_content = '\n'.join(
            f'  <tr>\n'
            f'    <td>{Index.get_object_ids_html([id_])}</td>\n'
            f'    <td>{Index.get_figure_links_html(figure_ids)}</td>\n'
            f'  </tr>'
            for id_, figure_ids in sorted(figure_ids_from_id.items())
        )

        return (
            f'<table>\n'
            f'<thead>\n'
            f'  <tr>\n'
            f'    <th>Object</th>\n'
            f'    <th>Figures</th>\n'
            f'  </tr>\n'
            f'</thead>\n'
            f'<tbody>\n'
            f'{tbody_rows_content}\n'
            f'</tbody>\n'
            f'</table>\n'
        )

    def get_figure_lookup_table_html(self):
        ids_from_figure_id = self.ids_from_figure_id

        tbody_rows_content = '\n'.join(
            f'  <tr>\n'
            f'    <td>{Index.get_figure_links_html([figure_id])}</td>\n'
            f'    <td>{Index.get_object_ids_html(ids)}</td>\n'
            f'  </tr>'
            for figure_id, ids in sorted(ids_from_figure_id.items())
        )

        return (
            f'<table>\n'
            f'<thead>\n'
            f'  <tr>\n'
            f'    <th>Figure</th>\n'
            f'    <th>Objects</th>\n'
            f'  </tr>\n'
            f'</thead>\n'
            f'<tbody>\n'
            f'{tbody_rows_content}\n'
            f'</tbody>\n'
            f'</table>\n'
        )

    @staticmethod
    def get_figure_links_html(figure_ids):
        return ', '.join(
            f'<a href="{escape_xml(figure_id)}.svg">'
            f'<code>{escape_xml(figure_id)}.svg</code>'
            f'</a>'
            for figure_id in sorted(figure_ids)
        )

    @staticmethod
    def get_object_ids_html(ids):
        return ', '.join(
            f'<code>{escape_xml(id_)}</code>'
            for id_ in sorted(ids)
        )

    def write_html(self, file_name):
        html_content = self.get_html_content()
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(html_content)
