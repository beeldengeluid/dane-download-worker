import os
from pathlib import Path
import logging
import validators


LOG_FORMAT = "%(asctime)s|%(levelname)s|%(process)d|%(module)s|%(funcName)s|%(lineno)d|%(message)s"
FILE_SIZE_UNITS = {"B": 1, "KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}
logger = logging.getLogger(__name__)


def parse_file_size(size):
    if " " not in size:  # no space in size, assume last 2 char are unit
        size = f"{size[:-2]} {size[-2:]}"

    number, unit = [s.strip() for s in size.upper().split()]
    try:
        return int(float(number) * FILE_SIZE_UNITS[unit])
    except ValueError:  # unit was longer than 2 chars, so number becomes a string
        return -1
    except KeyError:  # invalid unit was supplied
        return -1


def validate_config(config, validate_file_paths=True):
    try:
        __validate_environment_variables()
    except AssertionError as e:
        print("Error malconfigured worker: env vars incomplete")
        print(str(e))
        return False

    parent_dirs_to_check = []  # parent dirs of file paths must exist
    # check the DANE.cfg (supplied by config.yml)
    try:
        # rabbitmq settings
        assert config.RABBITMQ, "RABBITMQ"
        assert __check_setting(config.RABBITMQ.HOST, str), "RABBITMQ.HOST"
        assert __check_setting(config.RABBITMQ.PORT, int), "RABBITMQ.PORT"
        assert __check_setting(config.RABBITMQ.EXCHANGE, str), "RABBITMQ.EXCHANGE"
        assert __check_setting(
            config.RABBITMQ.RESPONSE_QUEUE, str
        ), "RABBITMQ.RESPONSE_QUEUE"
        assert __check_setting(config.RABBITMQ.USER, str), "RABBITMQ.USER"
        assert __check_setting(config.RABBITMQ.PASSWORD, str), "RABBITMQ.PASSWORD"

        # Elasticsearch settings
        assert config.ELASTICSEARCH, "ELASTICSEARCH"
        assert __check_setting(config.ELASTICSEARCH.HOST, list), "ELASTICSEARCH.HOST"
        assert (
            len(config.ELASTICSEARCH.HOST) == 1
            and type(config.ELASTICSEARCH.HOST[0]) == str
        ), "Invalid ELASTICSEARCH.HOST"

        assert __check_setting(config.ELASTICSEARCH.PORT, int), "ELASTICSEARCH.PORT"
        assert __check_setting(
            config.ELASTICSEARCH.USER, str, True
        ), "ELASTICSEARCH.USER"
        assert __check_setting(
            config.ELASTICSEARCH.PASSWORD, str, True
        ), "ELASTICSEARCH.PASSWORD"
        assert __check_setting(config.ELASTICSEARCH.SCHEME, str), "ELASTICSEARCH.SCHEME"
        assert __check_setting(config.ELASTICSEARCH.INDEX, str), "ELASTICSEARCH.INDEX"

        # logging
        assert config.LOGGING, "LOGGING"
        assert __check_setting(config.LOGGING.LEVEL, str), "LOGGING.LEVEL"
        assert __check_log_level(config.LOGGING.LEVEL), "Invalid LOGGING.LEVEL defined"
        assert __check_setting(config.LOGGING.DIR, str), "LOGGING.DIR"
        parent_dirs_to_check.append(config.LOGGING.DIR)

        # DANE python lib settings
        assert config.PATHS, "PATHS"
        assert __check_setting(config.PATHS.TEMP_FOLDER, str), "PATHS.TEMP_FOLDER"
        assert __check_setting(config.PATHS.OUT_FOLDER, str), "PATHS.OUT_FOLDER"

        # Settings for this DANE worker
        assert config.DOWNLOADER, "DOWNLOADER"
        assert __check_setting(
            config.DOWNLOADER.FS_THRESHOLD, str, True
        ), "DOWNLOADER.FS_THRESHOLD"
        if config.DOWNLOADER.FS_THRESHOLD:
            assert (
                parse_file_size(config.DOWNLOADER.FS_THRESHOLD) != -1
            ), "Invalid file size for DOWNLOADER.FS_THRESHOLD"
        assert __check_setting(
            config.DOWNLOADER.WHITELIST, list
        ), "DOWNLOADER.WHITELIST"
        for domain in config.DOWNLOADER.WHITELIST:
            assert validators.domain(
                domain
            ), f"Invalid domain in DOWNLOADER.WHITELIST: {domain}"

        # validate file paths (not while unit testing)
        if validate_file_paths:
            __validate_parent_dirs(parent_dirs_to_check)
            __validate_dane_paths(config.PATHS.TEMP_FOLDER, config.PATHS.OUT_FOLDER)

    except AssertionError as e:
        print(f"Configuration error: {str(e)}")
        return False

    return True


def __validate_environment_variables():
    # self.UNIT_TESTING = os.getenv('DW_DOWNLOAD_UNIT_TESTING', False)
    try:
        assert True
    except AssertionError as e:
        raise (e)


def __validate_dane_paths(dane_temp_folder: str, dane_out_folder: str):
    i_dir = Path(dane_temp_folder)
    o_dir = Path(dane_out_folder)

    try:
        assert os.path.exists(
            i_dir.parent.absolute()
        ), f"{i_dir.parent.absolute()} does not exist"
        assert os.path.exists(
            o_dir.parent.absolute()
        ), f"{o_dir.parent.absolute()} does not exist"
    except AssertionError as e:
        raise (e)


def __check_setting(setting, t, optional=False):
    return (type(setting) == t and optional is False) or (
        optional and (setting is None or type(setting) == t)
    )


def __check_log_level(level: str) -> bool:
    return level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def __validate_parent_dirs(paths: list) -> None:
    try:
        for p in paths:
            assert os.path.exists(
                Path(p).parent.absolute()
            ), f"Parent dir of file does not exist: {p}"
    except AssertionError as e:
        raise (e)
