import sys

class DeepRecurse:
    """
    Context manager for raising maximum recursion depth.
    """

    def __init__(self, recursion_limit):
        self.recursion_limit = recursion_limit

    def __enter__(self):
        self.old_recursion_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(self.recursion_limit)

    def __exit__(self, exception_type, exception_value, traceback):
        sys.setrecursionlimit(self.old_recursion_limit)
