import json
import os
import pytest
from mockito import unstub, when, verify
from worker import DownloadWorker
from DANE import Result, Document, Task
# from DANE import errors


DUMMY_DOWNLOAD_DIR = "/mnt/dane-fs/output-files"
DUMMY_FILE_PATH = "path/to/download/file.mp3"
DUMMY_DOC = Document(
    {
        "id": "dummy_id_12345",
        "url": "http://dummy-url.com/dummy.mp3",
        "type": "Video",
    },
    {"id": "UNIT TEST", "type": "Organization"},
)

DUMMY_TASK = Task.from_json(
    {"key": "DOWNLOAD", "state": 201, "msg": "Queued", "priority": 1}
)

DUMMY_RESULT = Result.from_json(
    json.dumps(
        {
            "generator": {
                "id": "dummy-id-12345",
                "type": "Software",
                "name": "DOWNLOAD",
                "homepage": "git@github.com:beeldengeluid/download-worker.git",
            },
            "payload": {
                "file_path": "/mnt/dane-fs/input-files/b8/21/63/b821637d36931b643241acd86626418bb7d50010/dummy.mp3",
                "file_type": "audio",
                "Content-Type": "audio/mpeg",
                "Content-Length": 5747355,
            },
        }
    )
)


def test_save_prior_download_result(config):
    try:
        w = DownloadWorker(config)

        when(w)._get_prior_download_results(DUMMY_DOC._id).thenReturn([DUMMY_RESULT])
        when(w)._copy_result(DUMMY_RESULT).thenReturn(DUMMY_RESULT)
        when(Result).save(DUMMY_TASK._id).thenReturn()

        resp = w._save_prior_download_result(DUMMY_DOC, DUMMY_TASK)
        assert resp is True
    finally:
        unstub()


@pytest.mark.parametrize(
    "file_exists, prior_result_saved, requires_download",
    [
        (True, True, False),
        (False, False, True),
        (False, True, True),
    ],
)
def test_requires_download(config, file_exists, prior_result_saved, requires_download):
    try:
        w = DownloadWorker(config)
        when(os.path).exists(DUMMY_FILE_PATH).thenReturn(file_exists)
        when(w)._save_prior_download_result(DUMMY_DOC, DUMMY_TASK).thenReturn(
            prior_result_saved
        )
        resp = w._requires_download(DUMMY_DOC, DUMMY_TASK, DUMMY_FILE_PATH)
        assert resp is requires_download

        # should always be called
        verify(os.path, times=1).exists(DUMMY_FILE_PATH)

        # should only be called if DUMMY_FILE_PATH exists
        verify(w, times=1 if file_exists else 0)._save_prior_download_result(
            DUMMY_DOC, DUMMY_TASK
        )
    finally:
        unstub()


@pytest.mark.parametrize(
    "url, whitelist, in_whitelist",
    [
        ("http://dummy.nl", ["dummy.nl"], True),
        ("http://dummy.nl/path/to", ["dummy.nl"], True),
        ("http://dummy.nl/path/to/file.mp3", ["dummy.nl"], True),
        ("http://dummy.nl", ["nodummy.nl"], False),  # not in whitelist, so should be False
        ("http://www.dummy.nl", ["dummy.nl"], False),  # www.DOMAIN is not recognized yet
    ],
)
def test_check_whitelist(config, url, whitelist, in_whitelist):
    try:
        w = DownloadWorker(config)
        assert w._check_whitelist(url, whitelist) is in_whitelist
    finally:
        unstub()


@pytest.mark.parametrize(
    "threshold, file_within_threshold",
    [
        (10 ** 6, True),  # 1MB
        (10 ** 7 -1, True),  # 10MB minus one byte
        (10 ** 7, False),  # 10MB is the same as the bytes free, which is not accepted
        (10 ** 8, False),  # 100MB
        (10 ** 9, False),  # 1GB
    ],
)
def test_check_download_threshold(config, threshold, file_within_threshold):
    try:
        w = DownloadWorker(config)
        when(w)._get_bytes_free(DUMMY_DOWNLOAD_DIR).thenReturn(10 ** 7)  # 10 MB free
        assert w._check_download_threshold(threshold, DUMMY_DOWNLOAD_DIR) is file_within_threshold
        verify(w, times=1)._get_bytes_free(DUMMY_DOWNLOAD_DIR)
    finally:
        unstub()
