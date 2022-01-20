import os

import disco

GENERIC_COST_DATABASE = os.path.join(
    disco.__path__[0],
    "postprocess",
    "config",
    "Generic_DISCO_cost_database_v2.xlsx"
)

UPGRADE_PARAMS_FILE = os.path.join(
    disco.__path__[0],
    "postprocess",
    "config",
    "upgrade_params.toml"
)
