
import logging


logger = logging.getLogger(__name__)


def create_analysis_config(analysis_type, overrides=None):
    # dynamically get class from analysis module
    module = __import__("disco.analysis", fromlist=[analysis_type])
    analysis_class = getattr(module, analysis_type)
    analysis_config = analysis_class()

    if overrides:
        try:
            analysis_config.set_config_overrides(overrides)
        except ValueError:
            logging.exception("Failed to set config overrides")
            raise

    return analysis_config
