"""
This test case validates the handling of nested structures.
"""

def outer_function():
    """
    An outer function.

    Returns:
        int: Always returns 1.
    """
    def inner_function():
        """
        An inner function.

        Returns:
            int: Always returns 2.
        """
        return 2

    return 1

class OuterClass:
    """
    An outer class.

    Attributes:
        outer_attr (str): An attribute of the outer class.
    """
    outer_attr = "Outer"

    class InnerClass:
        """
        An inner class.

        Attributes:
            inner_attr (str): An attribute of the inner class.
        """
        inner_attr = "Inner"

        def inner_method(self):
            """
            A method of the inner class.

            Returns:
                str: A string from the inner method.
            """
            return "Inner Method"