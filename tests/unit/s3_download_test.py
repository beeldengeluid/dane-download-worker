import pytest
import boto3
import os
from mockito import when, ARGS, KWARGS, mock
import s3_download
from model import DownloadResult, DANEResponse
import codecs

# from mockito import when

DUMMY_BUCKET = "assets"
DUMMY_FILE = "test.mp3"
DUMMY_SUB_DIR = "path/forward"
DUMMY_KEY = f"{DUMMY_SUB_DIR}/{DUMMY_FILE}"
DUMMY_S3_URI = f"s3://{DUMMY_BUCKET}/{DUMMY_KEY}"
DUMMY_DOWNLOAD_DIR = "download"


@pytest.mark.parametrize(
    "uri, expected_outcome",
    [
        (f"{DUMMY_BUCKET}/{DUMMY_FILE}", False),
        (f"http://{DUMMY_BUCKET}/{DUMMY_FILE}", False),
        (f"s3://{DUMMY_BUCKET}", False),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_FILE}", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}/{DUMMY_FILE}", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}/;semicolons;", True),
        (f"s3://{DUMMY_BUCKET}/{DUMMY_SUB_DIR}/url%20encodings", True),
    ],
)
def test_validate_s3_uri(uri, expected_outcome):
    assert s3_download.validate_s3_uri(uri) == expected_outcome


@pytest.mark.parametrize(
    "uri",
    [("s" * i) for i in range(0, 10)],
)
def test_deconstruct_s3_uri__always_returns_string(uri):
    bucket, key, fn = s3_download.deconstruct_s3_uri(uri)
    assert all(type(x) == str for x in [bucket, key, fn])


@pytest.mark.parametrize(
    "uri, download_dir",
    [
        (DUMMY_S3_URI, DUMMY_DOWNLOAD_DIR),
        ("", DUMMY_DOWNLOAD_DIR),
        (DUMMY_S3_URI, ""),
        (DUMMY_S3_URI, None),
        (None, DUMMY_DOWNLOAD_DIR),
        (None, None),
    ],
)
def test_download_s3_uri__always_returns_download_result(uri, download_dir):
    s3_client_mock = mock({"download_fileobj": lambda x, y, z: None})
    with when(boto3).client("s3").thenReturn(s3_client_mock), when(
        s3_client_mock
    ).download_fileobj(**KWARGS).thenReturn():
        result = s3_download.download_s3_uri(uri, download_dir)
        assert isinstance(result, DownloadResult)
        assert isinstance(result.dane_response, DANEResponse)


@pytest.mark.parametrize(
    "uri, download_dir",
    [  # either incorrect S3 URI or download dir
        (f"{DUMMY_BUCKET}/{DUMMY_FILE}", DUMMY_DOWNLOAD_DIR),
        (f"http://{DUMMY_BUCKET}/{DUMMY_FILE}", DUMMY_DOWNLOAD_DIR),
        (f"s3://{DUMMY_BUCKET}", DUMMY_DOWNLOAD_DIR),
        (DUMMY_S3_URI, None),
        (DUMMY_S3_URI, 1),
    ],
)
def test_download_s3_uri__400(uri, download_dir):
    result = s3_download.download_s3_uri(uri, download_dir)
    assert result.dane_response.state == 400


def test_download_s3_uri__200():
    s3_client_mock = mock({"download_fileobj": lambda x, y, z: None})
    fd_mock = mock({"__enter__": lambda: None, "__exit__": lambda x, y, z: None})
    with when(boto3).client("s3").thenReturn(s3_client_mock), when(
        s3_client_mock
    ).download_fileobj(**KWARGS).thenReturn(), when(s3_download).validate_download_dir(
        DUMMY_DOWNLOAD_DIR
    ).thenReturn(
        True
    ), when(
        codecs
    ).open(
        *ARGS
    ).thenReturn(
        fd_mock
    ):
        result = s3_download.download_s3_uri(
            DUMMY_S3_URI, DUMMY_DOWNLOAD_DIR
        )  # good uri and download dir
        assert result.dane_response.state == 200


def test_download_s3_uri__200_already_downloaded():
    s3_client_mock = mock({"download_fileobj": lambda x, y, z: None})
    with when(boto3).client("s3").thenReturn(s3_client_mock), when(
        s3_client_mock
    ).download_fileobj(**KWARGS).thenReturn(), when(s3_download).validate_download_dir(
        DUMMY_DOWNLOAD_DIR
    ).thenReturn(
        True
    ), when(
        os.path
    ).exists(
        *ARGS
    ).thenReturn(
        True
    ):
        result = s3_download.download_s3_uri(
            DUMMY_S3_URI, DUMMY_DOWNLOAD_DIR
        )  # good uri and download dir
        assert result.dane_response.state == 200


def test_download_s3_uri__500():
    s3_client_mock = mock({"download_fileobj": lambda x, y, z: None})
    with when(boto3).client("s3").thenReturn(s3_client_mock), when(
        s3_client_mock
    ).download_fileobj(**KWARGS).thenReturn(), when(s3_download).validate_download_dir(
        DUMMY_DOWNLOAD_DIR
    ).thenReturn(
        True
    ), when(
        codecs
    ).open(
        *ARGS
    ).thenRaise(
        Exception
    ):
        result = s3_download.download_s3_uri(
            DUMMY_S3_URI, DUMMY_DOWNLOAD_DIR
        )  # good uri and download dir
        assert result.dane_response.state == 500
