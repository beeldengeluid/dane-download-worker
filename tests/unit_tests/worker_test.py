from mockito import unstub  # , ANY, when
from base_util import validate_config

# from worker import DownloadWorker


def test_settings(config, environment_variables):
    try:
        assert validate_config(config, False)
    finally:
        unstub()
