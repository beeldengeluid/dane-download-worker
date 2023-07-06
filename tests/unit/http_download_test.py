# import pytest
# from mockito import unstub
from http_download import (
    download_http,
    extract_file_info,
)


def test_download_http():
    assert callable(download_http)


def test_extract_file_info():
    assert callable(extract_file_info)
