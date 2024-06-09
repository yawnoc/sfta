import textwrap
from math import sqrt

from .gate import Gate
from .event import Event
from .utilities import blunt, escape_xml, dull
from .utilities import FAULT_TREE_MAX_SIGNIFICANT_FIGURES as MAX_SIGNIFICANT_FIGURES


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
                    raise RuntimeError(f'Implementation error: Gate `type_` is neither `TYPE_AND` nor `TYPE_OR`.')
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
                f'Implementation error: `{id_}` is in neither `event_from_id` nor `gate_from_id`.'
            )

        implicated_ids = {
            id_,
            *{id_ for node in input_nodes for id_ in node.implicated_ids},
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
                x,
                y,
                quantity_value,
                quantity_type,
                hath_multiple_writs,
                time_unit,
            ),
        ]
        input_elements = [input_node.get_svg_elements_recursive() for input_node in self.input_nodes]

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
            slot_x = round(symbol_centre + slot_bias * Node.SYMBOL_SLOTS_HALF_WIDTH)

            if input_number in input_numbers_left:
                left_number = input_numbers_left.index(input_number) + 1
                bus_bias = 2 * left_number / (1 + left_input_count) - 1
            elif input_number in input_numbers_right:
                right_number = input_numbers_right.index(input_number) + 1
                bus_bias = 1 - 2 * right_number / (1 + right_input_count)
            else:
                bus_bias = 0
            bus_y = round(bus_middle + bus_bias * Node.CONNECTOR_BUS_HALF_HEIGHT)

            input_label_centre = input_node.x
            input_label_middle = input_node.y + Node.LABEL_BOX_Y_OFFSET

            points_by_input.append(
                ' '.join(
                    [
                        f'{slot_x},{symbol_middle}',
                        f'{slot_x},{bus_y}',
                        f'{input_label_centre},{bus_y}',
                        f'{input_label_centre},{input_label_middle}',
                    ]
                )
            )

        return '\n'.join(f'<polyline points="{points}"/>' for points in points_by_input)

    @staticmethod
    def label_rectangle_element(x, y):
        left = x - Node.LABEL_BOX_WIDTH // 2
        top = y - Node.LABEL_BOX_HEIGHT // 2 + Node.LABEL_BOX_Y_OFFSET
        width = Node.LABEL_BOX_WIDTH
        height = Node.LABEL_BOX_HEIGHT

        return f'<rect x="{left}" y="{top}" width="{width}" height="{height}"/>'

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
            1.0,
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

            text_elements.append(f'<text x="{centre}" y="{line_middle}" style="{style}">{content}</text>')

        return '\n'.join(text_elements)

    @staticmethod
    def id_rectangle_element(x, y):
        left = x - Node.ID_BOX_WIDTH // 2
        top = y - Node.ID_BOX_HEIGHT // 2 + Node.ID_BOX_Y_OFFSET
        width = Node.ID_BOX_WIDTH
        height = Node.ID_BOX_HEIGHT

        return f'<rect x="{left}" y="{top}" width="{width}" height="{height}"/>'

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

        return f'<rect x="{left}" y="{top}" width="{width}" height="{height}"/>'

    @staticmethod
    def quantity_text_element(
        x,
        y,
        quantity_value,
        quantity_type,
        hath_multiple_writs,
        time_unit,
    ):
        centre = x
        middle = y + Node.QUANTITY_BOX_Y_OFFSET

        if quantity_type == Event.TYPE_PROBABILITY:
            lhs = 'Q'
        elif quantity_type == Event.TYPE_RATE:
            lhs = 'w'
        else:
            raise RuntimeError('Implementation error: `quantity_type` is neither `TYPE_PROBABILITY` nor `TYPE_RATE`')

        if hath_multiple_writs:
            relation = '≤'
        else:
            relation = '='

        value_str = dull(quantity_value, MAX_SIGNIFICANT_FIGURES)
        unit_str = Event.quantity_unit_str(quantity_type, time_unit, suppress_unity=True)

        content = escape_xml(f'{lhs} {relation} {value_str}{unit_str}')

        return f'<text x="{centre}" y="{middle}">{content}</text>'
