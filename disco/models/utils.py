import os
from collections import UserDict
from typing import Any, List


class SchemaDict(UserDict):

    @property
    def title(self) -> str:
        return self.data.get("title", "")

    @property
    def description(self) -> str:
        return self.data.get("description", "")

    @property
    def type(self) -> Any:
        return self.data("type", None)

    @property
    def required(self) -> List[str]:
        return self.data.get("required", [])

    @property
    def properties(self) -> dict:
        return self.data.get("properties", {})

    @property
    def definitions(self) -> dict:
        return self.data.get("definitions", {})

    @property
    def optional(self) -> List[str]:
        return [prop for prop in self.properties if prop not in self.required]

    def get_refs(self, prop):
        """Given a property, find its model references,
        and the sub model references in schema.

        Parameters
        ----------
        prop : str
            Property name in the model.

        Returns
        -------
        list
            A list of model names referred by the property.
        """
        if (prop not in self.properties) or ("allOf" not in self.properties[prop]):
            return []

        stack = [
            os.path.basename(item["$ref"]) for item in self.properties[prop]["allOf"]
        ]

        refs = set()
        while stack:
            ref = stack.pop()
            refs.add(ref)

            for _prop in self.definitions[ref]["properties"]:
                _prop_data = self.definitions[ref]["properties"][_prop]
                if "allOf" not in _prop_data:
                    continue
                _refs = [os.path.basename(item["$ref"]) for item in _prop_data["allOf"]]
                stack.extend(_refs)

        return list(refs)

    def remove_property(self, prop):
        if prop in self.properties:
            del self.properties[prop]

    def remove_properties(self, props):
        for prop in props:
            self.remove_property(prop)

    def remove_definition(self, ref):
        if ref in self.definitions:
            del self.definitions[ref]

    def remove_definitions(self, refs):
        for ref in refs:
            self.remove_definition(ref)


def remove_key_from_dict(data, key):
    """Remove key from dict data recursively.

    Parameters
    ----------
    data : dict
        The dict data
    key : Any
        The key value
    """
    if not isinstance(data, dict):
        return

    if key in data:
        del data[key]

    for value in data.values():
        if not isinstance(value, dict):
            continue
        remove_key_from_dict(value, key)
