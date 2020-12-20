"""Defines Analysis objects."""

from abc import ABC, abstractmethod
from numpy import bool_

from jade.utils.utils import load_data


class Analysis(ABC):
    """Base Analysis class containing required inputs and options

    Attributes
    ----------
    inputs : list (default empty list)
    options : list (default empty list)

    """
    INPUTS = []
    OPTIONS = []

    def __init__(self, overrides=None, job_name=None):
        if overrides is not None:
            self.set_config_overrides(overrides)
        self._job_name = job_name
        self._results = []

    @abstractmethod
    def run(self):
        """Function to run when analysis has been built"""

    def get_option(self, option_name):
        """Return option with given name
        Parameters
        ----------
        option_name : str

        Returns
        -------
        Option

        """
        for option_config in self.get_options():
            if option_config.name == option_name:
                return option_config

        return None

    def get_input(self, input_name):
        """Return input with given name
        Parameters
        ----------
        input_name : str

        Returns
        -------
        Input

        """
        for input_config in self.get_inputs():
            if input_config.name == input_name:
                return input_config

        return None

    def print_inputs(self):
        """Prints name, type and default values for all inputs"""
        for analysis_input in self.INPUTS:
            name = analysis_input.name
            input_type = analysis_input.input_type.get_type_name()
            default_value = analysis_input.default

            if input_type == "dict":
                maxlen = max([len(k) for k in default_value.keys()])
                template = "\n{:<{width}}   {}\n".format("Parameter", "Value", width=maxlen)
                for k, v in default_value.items():
                    if v is True:
                        v = "true"
                    elif v is False:
                        v = "false"
                    template += "{:<{width}} : {}\n".format(k, str(v), width=maxlen)
                default_value = template.rstrip()

            print(f"Name: {name}\n" +
                  f"Type: ({input_type})\n" +
                  f"Default: {default_value}\n")

    def get_options(self):
        """Return option list"""
        return self.OPTIONS[:]

    def get_inputs(self):
        """Return input list"""
        return self.INPUTS[:]

    def serialize_inputs(self):
        """Return serialized input list"""
        return [input.serialize() for input in self.INPUTS]

    def set_option_overrides(self, overrides):
        """Set option values, given optional list of overrides

        Parameters
        ----------
        overrides : list
            list of overrides

        """
        for index, required_option in enumerate(self.OPTIONS):
            user_option = None
            if required_option.name in overrides.keys() :
                user_option = overrides[required_option.name]

            if user_option is None or user_option == '':
                parsed_value = required_option.default

            required_option.value = parsed_value
            self.OPTIONS[index] = required_option

    def set_config_overrides(self, overrides):
        """Set config values, given dict of overrides

        Parameters
        ----------
        overrides : dict

        Raises
        ------
        ValueError
            Raised if given input does not match type of current content

        """
        for index, required_input in enumerate(self.INPUTS):
            user_input = overrides.get(required_input.name)
            if user_input is None or user_input == '':
                parsed_value = required_input.default
            else:
                parsed_value = required_input.input_type.parse_value(user_input)

            if parsed_value is None:
                raise ValueError('Please input valid value for ' + required_input.name)

            required_input.value = parsed_value
            self.INPUTS[index] = required_input

    def get_results(self):
        """Returns analysis results"""
        inputs = self.serialize_inputs()
        # remove default index
        for i in inputs:
            i.pop('default')
        return {'inputs': inputs, 'outputs': self._results}

    @property
    def serialized_data(self):
        """Returns all INPUTS, user or defaults, as a dictionary"""
        serialized_data = {}
        for data in self.serialize_inputs():
            serialized_data[data['name']] = data['value']
        return serialized_data

    def _add_to_results(self, result_type, data):
        """Appends given results to list of result dicts

        Parameters
        ----------
        result_type: str
        data: dict

        """
        new_result = {'result_type': result_type, 'data': serialize_results(data)}
        self._results.append(new_result)


def load_config_file(_, __, value):
    """Load config file
    Parameters
    ----------
    value : str
        config file location

    Returns
    -------
    dict
        loaded config file

    """
    if value is None:
        return None

    return load_data(value)


def load_custom_overrides(_, __, value):
    """Load custom overrides from user
    Parameters
    ----------
    value : list
        list of str (override_name=override_value)

    Returns
    -------
    dict
        user overrides

    """
    user_overrides = {}

    for override in value:
        override_name, override_value = override.split('=')
        user_overrides[override_name] = override_value
    return user_overrides


def serialize_results(data):
    """Serialize results to JSON parse-able values

    Parameters
    ----------
    data : dict

    Returns
    -------
    dict

    """
    if not isinstance(data, dict) and not isinstance(data, list):
        return data

    serialized = {}
    for key, value in data.items():
        if isinstance(value, bool_):
            value = bool(value)
        serialized[key] = value
    return serialized
