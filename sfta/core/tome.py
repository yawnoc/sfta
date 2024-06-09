import itertools

from sfta.core.utilities import EVENT_TYPE_RATE
from sfta.core.writ import Writ


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
            if index > 0 and tome.quantity_type == EVENT_TYPE_RATE
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
        input_quantity_types = [tome.quantity_type for tome in input_tomes]
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
