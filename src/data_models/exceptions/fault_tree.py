from .base import FaultTreeTextException

class FtSmotheredObjectDeclarationException(FaultTreeTextException):
    pass

class FtDanglingPropertySettingException(FaultTreeTextException):
    pass

class FtDuplicateIdException(FaultTreeTextException):
    pass

class FtBadIdException(FaultTreeTextException):
    pass

class FtBadLineException(FaultTreeTextException):
    pass

class FtTimeUnitAlreadySetException(FaultTreeTextException):
    pass

class FtUnrecognisedKeyException(FaultTreeTextException):
    pass

class FtCircularGateInputsException(FaultTreeTextException):
    pass
