import json
import os
import pytest
from mockito import unstub, ANY, when, verify
from worker import DownloadWorker
from DANE import Result, Document, Task
from DANE import errors

DUMMY_FILE_PATH = "path/to/donwload/file.mp3"
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
