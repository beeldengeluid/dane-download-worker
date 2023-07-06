import pytest
from mockito import unstub
from urllib.parse import quote
import requests
from http_util import (
    determine_stream_extension,
    extract_extension_from_content_disposition,
)


# TODO test the function internals a bit more (better: split up / improve the function)
@pytest.mark.parametrize(
    "url, extension",
    [
        # (
        #     "http://low-res-throttler/viz/DE_TOEKOMST_I-KRO000071S9",
        #     ".mp4",
        # ),
        (
            "https://www.nu.nl/",
            ".html",
        ),
    ],
)
def test_determine_stream_extension(url: str, extension: str):
    try:
        http_resp = requests.get(url)
        assert determine_stream_extension(http_resp) == extension
    finally:
        unstub()


# see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition
# see: https://datatracker.ietf.org/doc/html/rfc5987
@pytest.mark.parametrize(
    "content_disposition, expected_output",
    [
        ('filename="example.mp4"', ".mp4"),  # regular example
        ('filename="exam  ple.mp4"', ".mp4"),  # regular example
        ("filename*=UTF-8''{}".format(quote("exam%ple$.mp4")), ".mp4"),  # rfc5987
        ("filename*=iso-8859-1''{}".format(quote("exam%ple$.mp4")), ".mp4"),  # rfc5987
        (
            "filename*=iso-8859-1'en'{}".format(quote("exam%ple$.mp4")),
            ".mp4",
        ),  # rfc5987
        (
            "filename*=iso-8859-1'en{}".format(quote("exam%ple$.mp4")),
            ".mp4",
        ),  # broken '<lang>'
        (
            "filename*=iso-8859-1{}".format(quote("exam%ple$.mp4")),
            "",
        ),  # without '<lang>'
        ('attachment; filename="example.mp3"', ".mp3"),  # attachement
        (
            'form-data; name="example-field"; filename="example.jpg"',
            ".jpg",
        ),  # form data
        ('form-data; name="example-field"', ""),  # no filename
        ("dummy-video.mp4", ""),  # without filename= or filename*=
        ("asdfasdfadsf", ""),  # random string
    ],
)
def test_extract_extension_from_content_disposition(
    content_disposition, expected_output
):
    s = extract_extension_from_content_disposition(content_disposition)
    assert s == expected_output
    assert type(s) == str
