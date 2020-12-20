"""Defines custom types."""

from jade.utils.utils import interpret_datetime


class CustomType:
    """Custom type class allows for additional types outside of str, float, int, etc"""
    CUSTOM_TYPES = [
        'percent',
        'float',
        'int',
        'str',
        'list',
        'dict',
        'bool',
        'datetime',
    ]

    def __init__(self, expected_type):
        self._check_type(expected_type)
        self.expected_type = expected_type

    def get_type_name(self):
        """Either returns string type name or class name of CustomType"""
        if isinstance(self.expected_type, str):
            return self.expected_type

        return self.expected_type.__name__

    def parse_value(self, value):
        """Checks type against given type class and returns cast value

        Parameters
        ----------
        value : str

        Returns
        -------
        casted type or None

        """
        if isinstance(self.expected_type, str):
            return self._handle_custom(value)

        if self.expected_type is bool:
            return self._handle_bool(value)

        try:
            return self.expected_type(value)
        except ValueError:
            return None

    def _check_type(self, given_type):
        """Check if type is a valid custom type

        Parameters
        ----------
        given_type : cls | str

        Raises
        ------
        ValueError
            Raised if type is not a valid custom type

        """
        error = None

        if isinstance(given_type, str):
            if f"{given_type}" not in self.CUSTOM_TYPES:
                error = f"Invalid type: {given_type}"
        else:
            if f"{given_type.__name__}" not in self.CUSTOM_TYPES:
                error = f"Invalid type: {given_type}"

        if error is not None:
            raise ValueError(error)

    def _handle_custom(self, value):
        """Handle all custom types

        Parameters
        ----------
        value : str

        Returns
        -------
        casted type or None

        """
        if self.expected_type == 'percent':
            return float(value)
        if self.expected_type == 'datetime':
            return interpret_datetime(value)

        return None

    @staticmethod
    def _handle_bool(value):
        """Handle bool-like values,
        For example: True/False, TRUE/FALSE, true/false, 1/0

        Parameters
        ----------
        value : str

        Returns
        -------
        casted type or None

        """
        if isinstance(value, bool):
            return value

        if value.lower() in ["true", "1", 1]:
            return True

        if value.lower() in ["false", "0", 0]:
            return False

        return None
