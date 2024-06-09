from .exceptions.event import (
    EventBadFloatException,
    EventBadProbabilityException,
    EventBadRateException,
    EventCommentAlreadySetException,
    EventLabelAlreadySetException,
    EventQuantityAlreadySetException,
    EventQuantityNotSetException,
)
from .tome import Tome, Writ
from .utilities import EVENT_KEY_EXPLAINER, EVENT_TYPE_PROBABILITY, EVENT_TYPE_RATE, EVENT_STR_FROM_TYPE


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

    KEY_EXPLAINER = EVENT_KEY_EXPLAINER

    TYPE_PROBABILITY = EVENT_TYPE_PROBABILITY
    TYPE_RATE = EVENT_TYPE_RATE

    STR_FROM_TYPE = EVENT_STR_FROM_TYPE

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

        raise RuntimeError('Implementation error: `quantity_type` is neither `TYPE_PROBABILITY` nor `TYPE_RATE`')

    def set_label(self, label, line_number):
        if self.label is not None:
            raise EventLabelAlreadySetException(
                line_number,
                f'label hath already been set for Event `{self.id_}` at line {self.label_line_number}'
            )

        self.label = label
        self.label_line_number = line_number

    def set_probability(self, probability_str, line_number):
        if self.quantity_type is not None:
            raise EventQuantityAlreadySetException(
                line_number,
                f'probability or rate hath already been set for Event `{self.id_}` at line {self.quantity_line_number}',
            )

        try:
            probability = float(probability_str)
        except ValueError:
            raise EventBadFloatException(
                line_number,
                f'unable to convert `{probability_str}` to float for Event `{self.id_}`',
            )

        if probability < 0:
            raise EventBadProbabilityException(
                line_number,
                f'probability `{probability_str}` is negative for Event `{self.id_}`',
            )
        if probability > 1:
            raise EventBadProbabilityException(
                line_number,
                f'probability `{probability_str}` exceedeth 1 for Event `{self.id_}`',
            )

        self.quantity_type = Event.TYPE_PROBABILITY
        self.quantity_value = probability
        self.quantity_line_number = line_number

    def set_rate(self, rate_str, line_number):
        if self.quantity_type is not None:
            raise EventQuantityAlreadySetException(
                line_number,
                f'probability or rate hath already been set for Event `{self.id_}` at line {self.quantity_line_number}',
            )

        try:
            rate = float(rate_str)
        except ValueError:
            raise EventBadFloatException(
                line_number,
                f'unable to convert `{rate_str}` to float for Event `{self.id_}`',
            )

        if rate < 0:
            raise EventBadRateException(
                line_number,
                f'rate `{rate_str}` is negative for Event `{self.id_}`'
            )
        if not rate < float('inf'):
            raise EventBadRateException(
                line_number,
                f'rate `{rate_str}` is not finite for Event `{self.id_}`'
            )

        self.quantity_type = Event.TYPE_RATE
        self.quantity_value = rate
        self.quantity_line_number = line_number

    def set_comment(self, comment, line_number):
        if self.comment is not None:
            raise EventCommentAlreadySetException(
                line_number,
                f'comment hath already been set for Event `{self.id_}` at line {self.comment_line_number}',
            )

        self.comment = comment
        self.comment_line_number = line_number

    def validate_properties(self, line_number):
        if self.quantity_type is None or self.quantity_value is None:
            raise EventQuantityNotSetException(
                line_number,
                f'probability or rate hath not been set for Event `{self.id_}`',
            )

    def compute_tome(self):
        self.tome = Tome(Writ.to_writs(self.index), self.quantity_type)
