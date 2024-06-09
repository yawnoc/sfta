from .base import FaultTreeTextException


class EventLabelAlreadySetException(FaultTreeTextException):
    pass


class EventQuantityAlreadySetException(FaultTreeTextException):
    pass


class EventCommentAlreadySetException(FaultTreeTextException):
    pass


class EventBadFloatException(FaultTreeTextException):
    pass


class EventBadProbabilityException(FaultTreeTextException):
    pass


class EventBadRateException(FaultTreeTextException):
    pass


class EventUnrecognisedKeyException(FaultTreeTextException):
    pass


class EventQuantityNotSetException(FaultTreeTextException):
    pass
