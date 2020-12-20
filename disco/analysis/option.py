"""Defines Option objects."""

class Option:
    """Option class used to store analysis option values"""

    def __init__(self, name, default, value=None):
        self.name = name
        self.default = default
        self.value = value
