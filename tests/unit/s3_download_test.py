import pytest
from s3_download import (
    validate_s3_uri,
    deconstruct_s3_uri,
    download_s3_uri,
)

# from mockito import when

DUMMY_BUCKET = "assets"
DUMMY_FILE = "test.mp3"
DUMMY_SUB_DIR = "path/forward"
DUMMY_KEY = f"{DUMMY_SUB_DIR}/{DUMMY_FILE}"


@pytest.mark.parametrize(
    "uri, expected_outcome",
    [
        (f"s3://{DUMMY_BUCKET}", False),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}/{DUMMY_FILE}", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}/;semicolons;", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}/url%20encodings", True),
    ],
)
def test_validate_s3_uri(uri, expected_outcome):
    assert validate_s3_uri(uri) == expected_outcome


def test_deconstruct_s3_uri():
    assert True


def test_download_s3_uri():
    assert True
