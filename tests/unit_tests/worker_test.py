import pytest
from mockito import unstub  # , ANY, when
from base_util import validate_config, parse_file_size, url_to_safe_filename
from worker import DownloadWorker


def test_settings(config, environment_variables):
    try:
        assert validate_config(config, False)
    finally:
        unstub()


@pytest.mark.parametrize("size, bytes", [
    ("10MB", 10 ** 7 ),
    ("10 MB", 10 ** 7 ), # with spaces also is allowed
    ("1111MB", 1111 * 10 ** 6 ),
    ("100GB", 10 ** 11 ),
    ("1Megabyte", -1 ),  # unit string too long (should be 2 chars)
    ("1PB", -1 )  # invalid unit
])
def test_parse_file_size(size, bytes):
    try:
        assert parse_file_size(size) == bytes
    finally:
        unstub()

@pytest.mark.parametrize("url, fn", [
    ("http://www.nu.nl", "UUID"),
    (123123, None),
])
def test_url_to_safe_filename(url, fn):
    try:
        pretty_fn = url_to_safe_filename(url)

        if fn == "UUID":
            assert len(pretty_fn) == 36  # i.e. len(str(uuid.uuid4()))
        else:
            assert url_to_safe_filename(url) == fn
    finally:
        unstub()
