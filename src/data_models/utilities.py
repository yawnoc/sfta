# utilities.py

import re
from math import isfinite, log10, prod

from .nan import Nan

FAULT_TREE_MAX_SIGNIFICANT_FIGURES = 4
FAULT_TREE_KEY_EXPLAINER = (
    "Recognised keys for a fault tree property setting are:\n"
    "    time_unit (optional)."
)
FAULT_TREE_IDS_EXPLAINER = "IDs may only contain letters, digits, underscores, and hyphens."
FAULT_TREE_LINE_EXPLAINER = (
    "A line must have one of the following forms:\n"
    "    Event: <id>         (an Event declaration)\n"
    "    Gate: <id>          (a Gate declaration)\n"
    "    - <key>: <value>    (a property setting)\n"
    "    # <comment>         (a comment)\n"
    "    <a blank line>      (used before the next declaration)."
)
FAULT_TREE_PROPERTY_EXPLAINER = (
    "Setting of properties for the fault tree itself "
    "must be done at the start of the file, "
    "even before any Event or Gate hath been declared."
)

EVENT_KEY_EXPLAINER = (
    "Recognised keys for an Event property setting are:\n"
    "    label (optional)\n"
    "    probability or rate (exactly one required)\n"
    "    comment (optional)."
)

EVENT_TYPE_PROBABILITY = 0
EVENT_TYPE_RATE = 1

EVENT_STR_FROM_TYPE = {
    EVENT_TYPE_PROBABILITY: "probability",
    EVENT_TYPE_RATE: "rate",
}


def blunt(number, max_decimal_places):
    """
    Blunt a number to at most certain decimal places, as a string.
    """
    if number is None:
        return None

    if number == Nan:
        return Nan.STRING

    if number == 0:
        return "0"

    if not isfinite(number):
        return str(number)

    nice_string = f"{number :.{max_decimal_places}F}"
    nice_string = re.sub(r"[.]?0*$", "", nice_string)

    return nice_string


def dull(number, max_significant_figures=1, coerce_scientific_exponent=3):
    """
    Dull a number to at most certain significant figures, as a string.
    """
    if number is None:
        return None

    if number == Nan:
        return Nan.STRING

    if number == 0:
        return "0"

    if not isfinite(number):
        return str(number)

    if log10(abs(number)) < -(coerce_scientific_exponent - 1):
        nice_string = f"{number :.{max_significant_figures - 1}E}"
        nice_string = re.sub(r"[.]?0*(?=E)", "", nice_string)
    else:
        nice_string = f"{number :.{max_significant_figures}G}"
    nice_string = re.sub("(?<=E[+-])0+", "", nice_string)
    general_float = float(nice_string)
    general_int = round(general_float)

    if general_float == general_int:
        return str(general_int)

    return nice_string


def descending_product(factors):
    """
    Compute a product after sorting the factors in descending order.

    Needed to prevent cut set quantity computations from depending on
    event declaration order, because floating-point arithmetic is dumb:
        0.1 * 0.3 * 0.5 * 0.823 = 0.012344999999999998
        0.823 * 0.5 * 0.3 * 0.1 = 0.012345
    """
    return prod(sorted(factors, reverse=True))


def descending_sum(terms):
    """
    Compute a sum after sorting the terms in descending order.

    Needed to prevent cut set quantity computations from depending on
    event declaration order, because floating-point arithmetic is dumb:
        1e-9 + 2.5e-12 + 5e-13 + 5e-10 + 2.5e-12 = 1.5054999999999998e-09
        1e-9 + 5e-10 + 2.5e-12 + 2.5e-12 + 5e-13 = 1.5055e-09
    """
    return sum(sorted(terms, reverse=True))


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

    # No point keeping track of dead_nodes, which is never queried

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

        infected_nodes.discard(node)
        infection_chain.pop()

    while clean_nodes:
        first_clean_node = min(clean_nodes)
        infect(first_clean_node)

    return infection_cycles


def escape_xml(text):
    """
    Escape & (when not used in an entity), <, and >.

    We make the following assumptions:
    - Entity names are any run of up to 31 letters. As of 2022-04-18,
    the longest entity name is `CounterClockwiseContourIntegral`
    according to <https://html.spec.whatwg.org/entities.json>.
    Actually checking entity names is slow for very little return.
    - Decimal code points are any run of up to 7 digits.
    - Hexadecimal code points are any run of up to 6 digits.
    """
    ampersand_pattern = re.compile(
        """
            [&]
            (?!
                (?:
                    [a-z]{1,31}
                        |
                    [#] (?: [0-9]{1,7} | [x][0-9a-f]{1,6} )
                )
                [;]
            )
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )
    text = re.sub(ampersand_pattern, "&amp;", text)
    text = re.sub("<", "&lt;", text)
    text = re.sub(">", "&gt;", text)

    return text


def is_bad_id(string):
    return not re.fullmatch(r"[a-zA-Z0-9_-]+", string)
