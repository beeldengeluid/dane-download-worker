import pytest
from mockito import unstub
from urllib.parse import quote
from http_util import (
    extract_extension_from_content_disposition,
    determine_url_extension,
    url_to_safe_filename,
    preprocess_url,
    extract_filename_from_url,
    to_safe_filename,
)


DUMMY_DOMAIN = "dummy.com"
DUMMY_PATH = "path/forward"
DUMMY_FILE = "test.mp3"


# TODO test the function internals a bit more (better: split up / improve the function)
@pytest.mark.parametrize(
    "url, extension",
    [
        (
            "http://prd-app-bng-01.beeldengeluid.nl:8093/viz/DE_TOEKOMST_I-KRO000071S9",
            ".mp4",
        ),
        (
            "https://www.nu.nl/",
            ".html",
        ),
    ],
)
def test_determine_url_extension(url: str, extension: str):
    try:
        assert determine_url_extension(url) == extension
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


@pytest.mark.parametrize(
    "url",
    [
        (f"http://{DUMMY_DOMAIN}"),
        (f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}"),
        (f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/;semicolons;"),
        (f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/url%20encodings"),
    ],
)
def test_preprocess_url(url: str):
    try:
        preprocessed = preprocess_url(url)
        assert preprocessed and ";" not in preprocessed  # all semicolons are removed
        assert (
            preprocessed and "%" not in preprocessed
        )  # url is unquoted (i.e. no url encodings)
    finally:
        unstub()


@pytest.mark.parametrize(
    "url, expected_fn",
    [
        (
            f"http://{DUMMY_DOMAIN}",
            DUMMY_DOMAIN.replace(".", "_"),
        ),  # no path so prefix based on DOMAIN in fn
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}",
            "forward",
        ),  # return last path element as file name
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/",
            "forward",
        ),  # same for trailing slash in path
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/;semicolons;",
            "forward",
        ),  # url part after ; is put in url params
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/url%20encodings",
            "url%20encodings",
        ),  # url encoded does end up in path
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/{DUMMY_FILE}",
            DUMMY_FILE,
        ),  # filenames at the end, returned "as is"
    ],
)
def test_extract_filename_from_url(url: str, expected_fn: str):
    try:
        extracted = extract_filename_from_url(url)
        assert extracted and expected_fn in extracted
    finally:
        unstub()


@pytest.mark.parametrize(
    "unsafe_fn, safe_fn",
    [
        ("test file", "test_file"),  # spaces should be replaced by underscores
        ("testó", "testo"),  # ascii chars are normalized (also accents are removed)
        ("testóó", "testoo"),  # ascii chars are normalized (also accents are removed)
        ("test漢-chinese", "test-chinese"),  # non-ascii chars are filtered out
        ("testصلے-arabic", "test-arabic"),  # non-ascii chars are filtered out
        ("test.mp3", "test.mp3"),  # . is of course allowed (for extensions)
        ("test-file.mp3", "test-file.mp3"),  # dash is allowed
        ("test_file.mp3", "test_file.mp3"),  # underscore is allowed
    ],
)
def test_to_safe_filename(unsafe_fn: str, safe_fn: str):
    try:
        assert to_safe_filename(unsafe_fn) == safe_fn
    finally:
        unstub()


# now test the function that calls preprocess_url, extract_filename_from_url and to_safe_filename
@pytest.mark.parametrize(
    "url, safe_fn",
    [
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/test漢file.mp3",
            "testfile.mp3",
        ),  # non-ascii is filtered out
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/test file.mp3",
            "test_file.mp3",
        ),  # spaces replaces with _
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/test%20file.mp3",
            "test_file.mp3",
        ),  # first unquoted, the space replaced with _
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}/test_file.mp3/",
            "test_file.mp3",
        ),  # trailing slash no problem
        (
            f"http://{DUMMY_DOMAIN}/{DUMMY_PATH}",
            "forward",
        ),  # last path element is filename
        (
            f"http://{DUMMY_DOMAIN}/url%20encoded%20path",
            "url_encoded_path",
        ),  # last path element is filename
    ],
)
def test_url_to_safe_filename(url: str, safe_fn: str):
    # TODO verify that/how all sub functions are called
    try:
        assert url_to_safe_filename(url) == safe_fn
    finally:
        unstub()
