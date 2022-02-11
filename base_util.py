import string
import unicodedata
import uuid
import os
from urllib.parse import urlparse, unquote
from pathlib import Path
import logging
import validators
from logging.handlers import TimedRotatingFileHandler


VALID_FILENAME_CHARS = "-_. {}{}".format(string.ascii_letters, string.digits)
FILE_SIZE_UNITS = {"B": 1, "KB": 10 ** 3, "MB": 10 ** 6, "GB": 10 ** 9, "TB": 10 ** 12}


def parse_file_size(size):
    if " " not in size:  # no space in size, assume last 2 char are unit
        size = f"{size[:-2]} {size[-2:]}"

    number, unit = [s.strip() for s in size.upper().split()]
    print(number)
    print(unit)
    try:
        return int(float(number) * FILE_SIZE_UNITS[unit])
    except ValueError:  # unit was longer than 2 chars, so number becomes a string
        return -1
    except KeyError:  # invalid unit was supplied
        return -1


"""
# makes sure any URL is downloaded to a file with an OS friendly file name (that still is human readable)
def url_to_safe_filename(url, whitelist=VALID_FILENAME_CHARS, replace=" ", char_limit=255):
    if type(url) != str:
        return None

    # ; in the url is terrible, since it cuts off everything after the ; when running urlparse
    url = url.replace(";", "")

    # grab the url path
    url_path = urlparse(url).path

    # get the file/dir name from the URL (if any)
    url_file_name = os.path.basename(url_path)

    # also make sure to get rid of the URL encoding
    filename = unquote(url_file_name if url_file_name != "" else url_path)

    # if both the url_path and url_file_name are empty the filename will be meaningless, so then assign a random UUID
    filename = str(uuid.uuid4()) if filename in ["", "/"] else filename

    # replace spaces (or anything else passed in the replace param) with underscores
    for r in replace:
        filename = filename.replace(r, "_")

    # keep only valid ascii chars
    cleaned_filename = (
        unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
    )

    # keep only whitelisted chars
    cleaned_filename = "".join(c for c in cleaned_filename if c in whitelist)
    if len(cleaned_filename) > char_limit:
        print(
            "Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(
                char_limit
            )
        )
    return cleaned_filename[:char_limit]
"""

# TODO test the new function in DANE!
def url_to_safe_filename(url: str) -> str:
    prepped_url = preprocess_url(url)
    if prepped_url is None:
        return None

    unsafe_fn = extract_filename_from_url(prepped_url)

    return to_safe_filename(unsafe_fn)


def preprocess_url(url: str) -> str:
    if type(url) != str:
        return None

    # ; in the url is terrible, since it cuts off everything after the ; when running urlparse
    url = url.replace(";", "")

    # make sure to get rid of the URL encoding
    return unquote(url)


def extract_filename_from_url(url: str) -> str:
    if type(url) != str:
        return None

    # grab the url path
    url_path = urlparse(url).path
    if url_path.rfind("/") == len(url_path) - 1:
        url_path = url_path[:-1]
    url_host = urlparse(url).netloc

    # get the file/dir name from the URL (if any)
    fn = os.path.basename(url_path)

    # if the url_path is empty, the file name is meaningless, so return a string based on the url_host
    return (
        f"{url_host.replace('.', '_')}__{str(uuid.uuid4())}" if fn in ["", "/"] else fn
    )


def to_safe_filename(
    fn: str, whitelist: list = VALID_FILENAME_CHARS, char_limit: int = 255
) -> str:
    if type(fn) != str:
        return None

    # replace spaces with underscore (spaces in filenames aren't nice)
    fn = fn.replace(" ", "_")

    safe_fn = unicodedata.normalize("NFKD", fn).encode("ASCII", "ignore").decode()

    # keep only whitelisted chars
    safe_fn = "".join(c for c in safe_fn if c in whitelist)

    if len(safe_fn) > char_limit:
        print(
            "Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(
                char_limit
            )
        )
    return safe_fn[:char_limit]


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


def __validate_parent_dirs(paths: list) -> bool:
    try:
        for p in paths:
            assert os.path.exists(
                Path(p).parent.absolute()
            ), f"Parent dir of file does not exist: {p}"
    except AssertionError as e:
        raise (e)


def init_logger(config):
    logger = logging.getLogger("DANE-DOWNLOAD")
    logger.setLevel(config.LOGGING.LEVEL)
    # create file handler which logs to file
    if not os.path.exists(os.path.realpath(config.LOGGING.DIR)):
        os.makedirs(os.path.realpath(config.LOGGING.DIR), exist_ok=True)

    fh = TimedRotatingFileHandler(
        os.path.join(os.path.realpath(config.LOGGING.DIR), "DANE-download-worker.log"),
        when="W6",  # start new log on sunday
        backupCount=3,
    )
    fh.setLevel(config.LOGGING.LEVEL)
    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(config.LOGGING.LEVEL)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
