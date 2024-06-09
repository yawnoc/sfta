import re
from .utilities import descending_product, descending_sum, Nan, is_bad_id
from .tome import Tome, Writ
from .event import Event
from .exceptions.gate import (
    GateBadIsPagedException,
    GateBadTypeException,
    GateCommentAlreadySetException,
    GateConjunctionBadTypesException,
    GateDisjunctionBadTypesException,
    GateInputsAlreadySetException,
    GateInputsNotSetException,
    GateIsPagedAlreadySetException,
    GateLabelAlreadySetException,
    GateTypeAlreadySetException,
    GateTypeNotSetException,
    GateZeroInputsException,
)
from .exceptions.fault_tree import FaultTreeBadIdException


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
    OR_INPUTS_EXPLAINER = 'OR gate inputs must be either all probabilities or all rates.'

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
            raise GateLabelAlreadySetException(
                line_number,
                f'label hath already been set for Gate `{self.id_}` at line {self.label_line_number}',
            )

        self.label = label
        self.label_line_number = line_number

    def set_is_paged(self, is_paged, line_number):
        if self.is_paged is not None:
            raise GateIsPagedAlreadySetException(
                line_number,
                f'is_paged hath already been set for `{self.id_}` at line {self.is_paged_line_number}',
            )

        if is_paged not in ['True', 'False']:
            raise GateBadIsPagedException(
                line_number,
                f'bad is_paged `{is_paged}` for Gate `{self.id_}`\n\n{Gate.IS_PAGED_EXPLAINER}',
            )

        self.is_paged = is_paged
        self.is_paged_line_number = line_number

    def set_type(self, type_str, line_number):
        if self.type_ is not None:
            raise GateTypeAlreadySetException(
                line_number,
                f'type hath already been set for Gate `{self.id_}` at line {self.type_line_number}',
            )

        if type_str == 'OR':
            self.type_ = Gate.TYPE_OR
        elif type_str == 'AND':
            self.type_ = Gate.TYPE_AND
        else:
            raise GateBadTypeException(
                line_number,
                f'bad type `{type_str}` for Gate `{self.id_}`\n\n{Gate.TYPE_EXPLAINER}',
            )
        self.type_line_number = line_number

    def set_inputs(self, input_ids_str, line_number):
        if self.input_ids is not None:
            raise GateInputsAlreadySetException(
                line_number,
                f'inputs have already been set for Gate `{self.id_}` at line {self.inputs_line_number}',
            )

        ids = Gate.split_ids(input_ids_str)
        if not ids:
            raise GateZeroInputsException(
                line_number,
                f'no IDs could be extracted from inputs `{input_ids_str}` for Gate `{self.id_}`',
            )
        for id_ in ids:
            if is_bad_id(id_):
                raise FaultTreeBadIdException(
                    line_number,
                    f'bad ID `{id_}` among inputs for Gate `{self.id_}`',
                )

        self.input_ids = ids
        self.inputs_line_number = line_number

    def set_comment(self, comment, line_number):
        if self.comment is not None:
            raise GateCommentAlreadySetException(
                line_number,
                f'comment hath already been set for Gate `{self.id_}` at line {self.comment_line_number}',
            )

        self.comment = comment
        self.comment_line_number = line_number

    def validate_properties(self, line_number):
        if self.is_paged is None:
            self.is_paged = False
        if self.type_ is None:
            raise GateTypeNotSetException(
                line_number,
                f'type hath not been set for Gate `{self.id_}`',
            )
        if self.input_ids is None:
            raise GateInputsNotSetException(
                line_number,
                f'inputs have not been set for Gate `{self.id_}`',
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
                    f'Implementation error: `{input_id}` is in neither `event_from_id` nor `gate_from_id`.'
                )

        if self.type_ == Gate.TYPE_AND:
            try:
                self.tome = Tome.and_(*input_tomes)
            except Tome.ConjunctionBadTypesException as exception:
                indices = exception.non_first_rate_indices
                ids = [self.input_ids[index] for index in indices]
                raise GateConjunctionBadTypesException(
                    self.inputs_line_number,
                    f'non-first inputs of type rate for AND Gate `{self.id_}`:'
                    + '\n    '
                    + '\n    '.join(f'`{id_}` (input #{index+1}) hath type rate' for index, id_ in zip(indices, ids))
                    + f'\n\n{Gate.AND_INPUTS_EXPLAINER}',
                )
        elif self.type_ == Gate.TYPE_OR:
            try:
                self.tome = Tome.or_(*input_tomes)
            except Tome.DisjunctionBadTypesException as exception:
                type_strs = [Event.STR_FROM_TYPE[type_] for type_ in exception.input_quantity_types]
                ids = self.input_ids
                raise GateDisjunctionBadTypesException(
                    self.inputs_line_number,
                    f'inputs of different type for OR Gate `{self.id_}`:'
                    + '\n    '
                    + '\n    '.join(f'`{id_}` hath type {type_str}' for id_, type_str in zip(ids, type_strs))
                    + f'\n\n{Gate.OR_INPUTS_EXPLAINER}',
                )
        else:
            raise RuntimeError(f'Implementation error: Gate `type_` is neither `TYPE_AND` nor `TYPE_OR`.')

    def compute_quantity(self, quantity_value_from_event_index):
        self.cut_sets_indices = {Writ.to_event_indices(writ) for writ in self.tome.writs}
        self.quantity_type = self.tome.quantity_type
        self.quantity_value_from_cut_set_indices = {
            cut_set_indices: descending_product(
                quantity_value_from_event_index[event_index] for event_index in cut_set_indices
            )
            for cut_set_indices in self.cut_sets_indices
        }
        self.quantity_value = descending_sum(self.quantity_value_from_cut_set_indices.values())

    def compute_contributions(self, events):
        self.contribution_value_from_event_index = {
            event.index: descending_sum(
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
            for event_index, contribution_value in self.contribution_value_from_event_index.items()
        }
