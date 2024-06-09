import os
import shutil
from sfta.writing.index import Index


def create_directory_robust(directory_name):
    if os.path.isfile(directory_name):
        os.remove(directory_name)
    if os.path.isdir(directory_name):
        shutil.rmtree(directory_name)
    os.mkdir(directory_name)


def write_output_files(fault_tree, output_directory_name):
    svg_file_path = []
    events_table = fault_tree.get_events_table()
    gates_table = fault_tree.get_gates_table()
    cut_set_table_from_gate_id = fault_tree.get_cut_set_tables()
    contribution_table_from_gate_id = fault_tree.get_contribution_tables()
    figure_from_id = fault_tree.get_figures()

    cut_sets_directory_name = f"{output_directory_name}/cut-sets"
    contributions_directory_name = f"{output_directory_name}/contributions"
    figures_directory_name = f"{output_directory_name}/figures"

    create_directory_robust(cut_sets_directory_name)
    create_directory_robust(contributions_directory_name)
    create_directory_robust(figures_directory_name)

    figure_index = Index(figure_from_id, figures_directory_name)

    events_table.write_tsv(f"{output_directory_name}/events.tsv")
    gates_table.write_tsv(f"{output_directory_name}/gates.tsv")
    for gate_id, cut_set_table in cut_set_table_from_gate_id.items():
        cut_set_table.write_tsv(f"{cut_sets_directory_name}/{gate_id}.tsv")
    for gate_id, contribution_table in contribution_table_from_gate_id.items():
        contribution_table.write_tsv(f"{contributions_directory_name}/{gate_id}.tsv")
    for figure_id, figure in figure_from_id.items():
        figure.write_svg(f"{figures_directory_name}/{figure_id}.svg")
    figure_index.write_html(f"{figures_directory_name}/index.html")

    # go through the figures directory and get the path of all the svg files
    for root, _, files in os.walk(figures_directory_name):
        for file in files:
            if file.endswith(".svg"):
                svg_file_path.append(os.path.join(root, file))

    return svg_file_path
