import re

from .utilities import dull, find_cycles, is_bad_id
from .utilities import (
    FAULT_TREE_MAX_SIGNIFICANT_FIGURES,
    FAULT_TREE_KEY_EXPLAINER,
    FAULT_TREE_IDS_EXPLAINER,
    FAULT_TREE_LINE_EXPLAINER,
    FAULT_TREE_PROPERTY_EXPLAINER,
)
from .event import Event
from .gate import Gate
from .figure import Figure
from .table import Table
from .exceptations.fault_tree import (
    FtBadIdException, 
    FtSmotheredObjectDeclarationException, 
    FtDanglingPropertySettingException, 
    FtDuplicateIdException, 
    FtBadIdException, 
    FtBadLineException, 
    FtTimeUnitAlreadySetException, 
    FtUnrecognisedKeyException, 
    FtCircularGateInputsException
    )

from .exceptations.gate import GateUnknownInputException, GateUnrecognisedKeyException
from .exceptations.event import EventUnrecognisedKeyException


class FaultTree:
    def __init__(self, fault_tree_text):
        (
            self.event_from_id,
            self.gate_from_id,
            self.event_id_from_index,
            self.used_event_ids,
            self.top_gate_ids,
            self.time_unit,
        ) = FaultTree.build(fault_tree_text)

    MAX_SIGNIFICANT_FIGURES = FAULT_TREE_MAX_SIGNIFICANT_FIGURES
    KEY_EXPLAINER = FAULT_TREE_KEY_EXPLAINER
    IDS_EXPLAINER = FAULT_TREE_IDS_EXPLAINER
    LINE_EXPLAINER = FAULT_TREE_LINE_EXPLAINER
    PROPERTY_EXPLAINER = FAULT_TREE_PROPERTY_EXPLAINER

    @staticmethod
    def is_bad_id(string):
        return not re.fullmatch(r"[a-zA-Z0-9_-]+", string)

    @staticmethod
    def build(fault_tree_text):
        events, gates, time_unit = FaultTree.parse(fault_tree_text)
        event_id_from_index = {event.index: event.id_ for event in events}
        event_from_id = {event.id_: event for event in events}
        gate_from_id = {gate.id_: gate for gate in gates}

        used_event_ids, top_gate_ids = FaultTree.validate_gate_inputs(event_from_id, gate_from_id)
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

        lines = (fault_tree_text + "\n\n").splitlines()
        for line_number, line in enumerate(lines, start=1):

            object_line_regex = r"^(?P<class_>Event|Gate): \s*(?P<id_>.+?)\s*$"
            object_line_match = re.match(object_line_regex, line)
            if object_line_match:
                class_ = object_line_match.group("class_")
                id_ = object_line_match.group("id_")

                if current_object not in (None, FaultTree):
                    raise FtSmotheredObjectDeclarationException(
                        line_number, f"missing blank line before " f"declaration of {class_} `{id_}`"
                    )
                if id_ in ids:
                    raise FtDuplicateIdException(line_number, f"duplicate ID `{id_}` in declaration of {class_}")
                if is_bad_id(id_):
                    raise FtBadIdException(
                        line_number, f"bad ID `{id_}` in declaration of {class_}" f"\n\n{FaultTree.IDS_EXPLAINER}"
                    )

                if class_ == "Event":
                    event = Event(id_, event_index)
                    events.append(event)
                    event_index += 1
                    current_object = event
                elif class_ == "Gate":
                    gate = Gate(id_)
                    gates.append(gate)
                    current_object = gate
                else:
                    raise RuntimeError(
                        f"Implementation error: "
                        f"`class_` matched from regex `{object_line_regex}` "
                        f"is neither `Event` nor `Gate`."
                    )
                ids.add(id_)
                continue

            property_line_regex = r"^- (?P<key>\S+): \s*(?P<value>.+?)\s*$"
            property_line_match = re.match(property_line_regex, line)
            if property_line_match:
                key = property_line_match.group("key")
                value = property_line_match.group("value")

                if current_object is None:
                    raise FtDanglingPropertySettingException(
                        line_number,
                        f"missing Event or Gate declaration before "
                        f"setting {key} to `{value}`"
                        f"\n\n{FaultTree.PROPERTY_EXPLAINER}",
                    )

                if current_object is FaultTree:
                    if key == "time_unit":
                        if time_unit is not None:
                            raise FtTimeUnitAlreadySetException(
                                line_number, f"time unit hath already been set " f"at line {time_unit_line_number}"
                            )
                        time_unit = value
                        time_unit_line_number = line_number
                    else:
                        raise FtUnrecognisedKeyException(
                            line_number,
                            f"unrecognised key `{key}` " f"for the fault tree" f"\n\n{FaultTree.KEY_EXPLAINER}",
                        )
                elif isinstance(current_object, Event):
                    if key == "label":
                        current_object.set_label(value, line_number)
                    elif key == "probability":
                        current_object.set_probability(value, line_number)
                    elif key == "rate":
                        current_object.set_rate(value, line_number)
                    elif key == "comment":
                        current_object.set_comment(value, line_number)
                    else:
                        raise EventUnrecognisedKeyException(
                            line_number,
                            f"unrecognised key `{key}` "
                            f"for Event `{current_object.id_}`"
                            f"\n\n{Event.KEY_EXPLAINER}",
                        )
                elif isinstance(current_object, Gate):
                    if key == "label":
                        current_object.set_label(value, line_number)
                    elif key == "is_paged":
                        current_object.set_is_paged(value, line_number)
                    elif key == "type":
                        current_object.set_type(value, line_number)
                    elif key == "inputs":
                        current_object.set_inputs(value, line_number)
                    elif key == "comment":
                        current_object.set_comment(value, line_number)
                    else:
                        raise GateUnrecognisedKeyException(
                            line_number,
                            f"unrecognised key `{key}` " f"for Gate `{current_object.id_}`" f"\n\n{Gate.KEY_EXPLAINER}",
                        )
                else:
                    raise RuntimeError(
                        f"Implementation error: "
                        f"current_object {current_object} "
                        f"is an instance of neither Event nor Gate."
                    )
                continue

            comment_line_regex = "^#.*$"
            if re.match(comment_line_regex, line):
                continue

            blank_line_regex = r"^\s*$"
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
                        f"Implementation error: "
                        f"current_object {current_object} "
                        f"is an instance of neither Event nor Gate."
                    )
                continue

            raise FtBadLineException(line_number, f"bad line `{line}`" f"\n\n{FaultTree.LINE_EXPLAINER}")

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
                    raise GateUnknownInputException(
                        gate.inputs_line_number, f"no Event or Gate is ever declared with ID `{id_}`"
                    )

        return used_event_ids, top_gate_ids

    @staticmethod
    def validate_tree(gate_from_id):
        input_gate_ids_from_id = {
            id_: set(input_id for input_id in gate.input_ids if input_id in gate_from_id)  # exclude Events
            for id_, gate in gate_from_id.items()
        }

        cycles = find_cycles(input_gate_ids_from_id)
        if cycles:
            cycle = min(cycles)
            length = len(cycle)
            raise FtCircularGateInputsException(
                None,
                "circular gate inputs detected:"
                + "\n    "
                + "\n    ".join(
                    f"at line {gate_from_id[cycle[i]].inputs_line_number}: "
                    f"Gate `{cycle[i]}` hath input `{cycle[(i+1) % length]}`"
                    for i, _ in enumerate(cycle)
                ),
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
        quantity_value_from_event_index = {event.index: event.quantity_value for event in events}
        for gate in gates:
            gate.compute_quantity(quantity_value_from_event_index)

    @staticmethod
    def compute_gate_contributions(events, gates):
        for gate in gates:
            gate.compute_contributions(events)

    def get_events_table(self):
        field_names = [
            "id",
            "is_used",
            "quantity_type",
            "quantity_value",
            "quantity_unit",
            "label",
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
            "id",
            "is_top_gate",
            "is_paged",
            "quantity_type",
            "quantity_value",
            "quantity_unit",
            "type",
            "inputs",
            "label",
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
                ",".join(gate.input_ids),
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
                "quantity_type",
                "quantity_value",
                "quantity_unit",
                "cut_set",
                "cut_set_order",
            ]
            rows = [
                [
                    Event.STR_FROM_TYPE[gate.quantity_type],
                    dull(quantity_value, FaultTree.MAX_SIGNIFICANT_FIGURES),
                    Event.quantity_unit_str(
                        gate.quantity_type,
                        self.time_unit,
                    ),
                    ".".join(self.event_id_from_index[event_index] for event_index in sorted(cut_set_indices)),
                    len(cut_set_indices),
                ]
                for cut_set_indices, quantity_value in gate.quantity_value_from_cut_set_indices.items()
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
                "event",
                "contribution_type",
                "contribution_value",
                "contribution_unit",
                "importance",
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
                    ),
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
