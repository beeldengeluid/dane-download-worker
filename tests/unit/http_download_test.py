import pytest
from mockito import unstub
from http_download import (
    url_to_safe_filename,
    preprocess_url,
    extract_filename_from_url,
    to_safe_filename,
)

DUMMY_DOMAIN = "dummy.com"
DUMMY_PATH = "path/forward"
DUMMY_FILE = "test.mp3"


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
