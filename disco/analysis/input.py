"""Defines Input objects."""

import json


class Input:
    """Input class used to store analysis input values"""

    def __init__(self, name, input_type, default, value=None):
        self.name = name
        self.input_type = input_type
        self.default = default
        self.value = value

    def serialize(self):
        """Serializes input to dict"""
        return dict({
            'name': self.name,
            'input_type': self.input_type.get_type_name(),
            'default': self.default,
            'value': self.value
        })

    @property
    def current_value(self):
        """Get Input current value (converted if necessary)"""
        input_type = self.input_type.get_type_name()
        if input_type == 'percent':
            return self.value / 100

        return self.value

    def to_json(self):
        """Output variables to json string"""

        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
