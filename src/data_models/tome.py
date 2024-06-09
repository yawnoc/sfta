import itertools

from src.data_models.utilities import EVENT_TYPE_RATE


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
        return frozenset(index for index, digit in enumerate(bin(writ)[-1:1:-1]) if digit == "1")

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
            index for index, tome in enumerate(input_tomes) if index > 0 and tome.quantity_type == EVENT_TYPE_RATE
        ]
        if non_first_rate_indices:
            raise Tome.ConjunctionBadTypesException(non_first_rate_indices)

        conjunction_quantity_type = input_tomes[0].quantity_type

        writs_by_tome = (tome.writs for tome in input_tomes)
        writ_tuples_by_term = itertools.product(*writs_by_tome)
        conjunction_writs_by_term = (Writ.and_(*term_writ_tuple) for term_writ_tuple in writ_tuples_by_term)
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

        input_writs = (writ for tome in input_tomes for writ in tome.writs)
        disjunction_writs = Writ.or_(*input_writs)

        return Tome(disjunction_writs, disjunction_quantity_type)

    class ConjunctionBadTypesException(Exception):
        def __init__(self, non_first_rate_indices):
            self.non_first_rate_indices = non_first_rate_indices

    class DisjunctionBadTypesException(Exception):
        def __init__(self, input_quantity_types):
            self.input_quantity_types = input_quantity_types
