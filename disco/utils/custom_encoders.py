"""Utility functions for the disco package."""
import json
import enum
import numpy as np
from pathlib import PosixPath, WindowsPath


class ExtendedJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, enum.Enum):
            return obj.value

        if isinstance(obj, PosixPath) or isinstance(obj, WindowsPath):
            return str(obj)

        if isinstance(obj, np.int32):
            return int(obj)
        
        if isinstance(obj, np.int64):
            return int(obj)
        
        return json.JSONEncoder.default(self, obj)
    