class Nan:
    """
    Static class representing NaN (not a number).
    """

    def __new__(cls):
        raise TypeError("`Nan` cannot be instantiated")

    STRING = "nan"
