"""
This is a debug test case to validate specific edge cases for the documentation generator.
"""

# Global constant
global_constant = 42

def function_with_no_docstring():
    pass

def function_with_complex_signature(param1: int, param2: str = "default", *args, **kwargs):
    """
    Function with complex signature.

    Args:
        param1 (int): The first parameter.
        param2 (str): The second parameter with a default value.

    Returns:
        bool: Always returns True.
    """
    return True

class SampleClass:
    """
    A sample class for testing.

    Attributes:
        attribute (str): A sample attribute.
    """
    attribute = "Sample"

    def __init__(self, value: int):
        """
        Initializes the sample class.

        Args:
            value (int): The value to initialize with.
        """
        self.value = value

    def method_with_decorator(self):
        """
        A method with a decorator.

        Returns:
            str: A sample string.
        """
        return "decorated"

    @staticmethod
    def static_method():
        """
        A static method.

        Returns:
            str: A static string.
        """
        return "static"

    @classmethod
    def class_method(cls):
        """
        A class method.

        Returns:
            str: A class string.
        """
        return "class"