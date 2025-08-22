"""
Minimal test Python file.
"""

class MinimalClass:
    """
    A minimal class for testing.

    Attributes:
        attr1 (int): A sample attribute.
    """
    attr1 = 42

    def __init__(self, value):
        """
        Initializes MinimalClass.

        Args:
            value (int): The value to set attr1 to.
        """
        self.attr1 = value

    def method(self):
        """
        A sample method.

        Returns:
            str: A sample string.
        """
        return "sample"

def minimal_function():
    """
    A minimal function for testing.

    Returns:
        bool: True, always.
    """
    return True