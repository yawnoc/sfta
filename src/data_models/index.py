from .utilities import escape_xml
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
        meta_viewport = "<meta" ' name="viewport"' ' content="width=device-width, initial-scale=1"' ">"
        title = f"Index of `{figures_directory_name}/`"
        heading = f"Index of <code>{figures_directory_name}/</code>"

        object_lookup_table_html = self.get_object_lookup_table_html()
        figure_lookup_table_html = self.get_figure_lookup_table_html()

        return (
            f"<!DOCTYPE html>\n"
            f'<html lang="en">\n'
            f"<head>\n"
            f"  {meta_charset}\n"
            f"  {meta_viewport}\n"
            f"  <title>{title}</title>\n"
            f"  <style>\n"
            f"    html {{\n"
            f"      margin: 0 auto;\n"
            f"      max-width: 45em;\n"
            f"    }}\n"
            f"    table {{\n"
            f"      border-spacing: 0;\n"
            f"      border-collapse: collapse;\n"
            f"      margin-top: 0.5em;\n"
            f"      margin-bottom: 1em;\n"
            f"    }}\n"
            f"    th {{\n"
            f"      background-clip: padding-box;\n"
            f"      background-color: lightgrey;\n"
            f"      position: sticky;\n"
            f"      top: 0;\n"
            f"    }}\n"
            f"    th, td {{\n"
            f"      border: 1px solid black;\n"
            f"      padding: 0.4em;\n"
            f"    }}\n"
            f"  </style>\n"
            f"</head>\n"
            f"<body>\n"
            f"<h1>{heading}</h1>\n"
            f"<h2>Lookup by object</h2>"
            f"{object_lookup_table_html}"
            f"<h2>Lookup by figure</h2>"
            f"{figure_lookup_table_html}"
            f"</body>\n"
            f"</html>\n"
        )

    def get_object_lookup_table_html(self):
        figure_ids_from_id = self.figure_ids_from_id

        tbody_rows_content = "\n".join(
            f"  <tr>\n"
            f"    <td>{Index.get_object_ids_html([id_])}</td>\n"
            f"    <td>{Index.get_figure_links_html(figure_ids)}</td>\n"
            f"  </tr>"
            for id_, figure_ids in sorted(figure_ids_from_id.items())
        )

        return (
            f"<table>\n"
            f"<thead>\n"
            f"  <tr>\n"
            f"    <th>Object</th>\n"
            f"    <th>Figures</th>\n"
            f"  </tr>\n"
            f"</thead>\n"
            f"<tbody>\n"
            f"{tbody_rows_content}\n"
            f"</tbody>\n"
            f"</table>\n"
        )

    def get_figure_lookup_table_html(self):
        ids_from_figure_id = self.ids_from_figure_id

        tbody_rows_content = "\n".join(
            f"  <tr>\n"
            f"    <td>{Index.get_figure_links_html([figure_id])}</td>\n"
            f"    <td>{Index.get_object_ids_html(ids)}</td>\n"
            f"  </tr>"
            for figure_id, ids in sorted(ids_from_figure_id.items())
        )

        return (
            f"<table>\n"
            f"<thead>\n"
            f"  <tr>\n"
            f"    <th>Figure</th>\n"
            f"    <th>Objects</th>\n"
            f"  </tr>\n"
            f"</thead>\n"
            f"<tbody>\n"
            f"{tbody_rows_content}\n"
            f"</tbody>\n"
            f"</table>\n"
        )

    @staticmethod
    def get_figure_links_html(figure_ids):
        return ", ".join(
            f'<a href="{escape_xml(figure_id)}.svg">' f"<code>{escape_xml(figure_id)}.svg</code>" f"</a>"
            for figure_id in sorted(figure_ids)
        )

    @staticmethod
    def get_object_ids_html(ids):
        return ", ".join(f"<code>{escape_xml(id_)}</code>" for id_ in sorted(ids))

    def write_html(self, file_name):
        html_content = self.get_html_content()
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(html_content)
