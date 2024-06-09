from .base import FaultTreeTextException

class GateLabelAlreadySetException(FaultTreeTextException):
    pass

class GateIsPagedAlreadySetException(FaultTreeTextException):
    pass

class GateTypeAlreadySetException(FaultTreeTextException):
    pass

class GateInputsAlreadySetException(FaultTreeTextException):
    pass

class GateCommentAlreadySetException(FaultTreeTextException):
    pass

class GateBadIsPagedException(FaultTreeTextException):
    pass

class GateBadTypeException(FaultTreeTextException):
    pass

class GateZeroInputsException(FaultTreeTextException):
    pass

class GateUnrecognisedKeyException(FaultTreeTextException):
    pass

class GateTypeNotSetException(FaultTreeTextException):
    pass

class GateInputsNotSetException(FaultTreeTextException):
    pass

class GateUnknownInputException(FaultTreeTextException):
    pass

class GateConjunctionBadTypesException(FaultTreeTextException):
    pass

class GateDisjunctionBadTypesException(FaultTreeTextException):
    pass
