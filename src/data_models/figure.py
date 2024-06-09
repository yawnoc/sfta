from .node import Node


class Figure:
    MARGIN = 10

    def __init__(self, fault_tree, id_):
        event_from_id = fault_tree.event_from_id
        gate_from_id = fault_tree.gate_from_id
        time_unit = fault_tree.time_unit

        top_node = Node(event_from_id, gate_from_id, time_unit, id_, to_node=None)
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
