from .base import FaultTreeTextException


class FaultTreeSmotheredObjectDeclarationException(FaultTreeTextException):
    pass


class FaultTreeDanglingPropertySettingException(FaultTreeTextException):
    pass


class FaultTreeDuplicateIdException(FaultTreeTextException):
    pass


class FaultTreeBadIdException(FaultTreeTextException):
    pass


class FaultTreeBadLineException(FaultTreeTextException):
    pass


class FaultTreeTimeUnitAlreadySetException(FaultTreeTextException):
    pass


class FaultTreeUnrecognisedKeyException(FaultTreeTextException):
    pass


class FaultTreeCircularGateInputsException(FaultTreeTextException):
    pass
