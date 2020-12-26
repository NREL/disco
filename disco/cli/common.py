"""Common functions for CLI scripts"""

import logging
import logging.config
import os
import shutil

import click

from jade.exceptions import InvalidParameter, UserAbort
from disco.enums import Scale, Placement


logger = logging.getLogger(__name__)


_ENUM_MAPPING = {
    # class to type of value
    "placement": (Placement, str),
    "scale": (Scale, str)
}


def handle_enum_input(_, param, value):
    """Converts inputs to enums."""
    try:
        tup = _ENUM_MAPPING.get(param.name)
        assert tup is not None, "Must add {} to _ENUM_MAPPING".format(
            param.name)
        # Force the correct type onto the value.
        return tup[0](tup[1](value))
    except ValueError as err:
        raise click.BadParameter(str(err))


def _handle_simulation_scripts(ctx, _, value):
    if not os.path.exists(value):
        logger.info("Creating %s...", value)
        try:
            os.makedirs(value)
        except Exception as err:
            logger.error("Could not create %s: %s", value, err)
            raise
    else:
        proceed_with_user_permission(ctx, "Overwrite {}".format(value))
        try:
            scripts = [f for f in os.listdir(value) if f.endswith(".sh")]
            for s in scripts:
                os.remove(os.path.join(value, s))
        except Exception as err:
            logger.error("Could not delete %s: %s", value, err)
            raise

    return value


def handle_existing_dir(directory, force):
    """Deletes existing directory if force is True."""
    if os.path.exists(directory):
        if force:
            shutil.rmtree(directory)
            os.mkdir(directory)
        else:
            raise InvalidParameter(f"directory={directory} exists. Set --force to overwrite")


def proceed_with_user_permission(ctx, message):
    """Pauses execution to prompt user for permission to proceed."""
    prompt = ctx.params.get("prompt")
    if prompt is None:
        prompt = ctx.parent.params["prompt"]
    if not prompt:
        logger.info("Proceed because user passed --no-prompt.")
        return

    answer = ""
    while answer not in ("y", "n"):
        answer = input("{} [Y/N]? ".format(message)).lower()

    if answer == "n":
        raise UserAbort
