"""
Test Python file for documentation generator.
"""

class TestClass:
    """
    This is a test class.

    Attributes:
        attr1 (str): Description of attr1.
    """
    attr1 = "default"

    def __init__(self, value):
        """
        Initializes the TestClass.

        Args:
            value (str): The value to set attr1 to.
        """
        self.attr1 = value

    def method(self):
        """
        A test method.

        Returns:
            str: A test string.
        """
        return "test"


def test_function():
    """
    A test function.

    Returns:
        bool: True, always.
    """
    return True