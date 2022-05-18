import json
import os
import pytest
from mockito import unstub, when, verify
from worker import DownloadWorker
from dane import Result, Document, Task
from dane import errors


DUMMY_DOWNLOAD_DIR = "/mnt/dane-fs/output-files"
DUMMY_FILE_PATH = "path/to/download/file.mp3"
DUMMY_DANE_DIRS = {
    "TEMP_FOLDER": "/mnt/dane-fs/input-dir",
    "OUT_FOLDER": "/mnt/dane-fs/output-dir",
}
DUMMY_DOC = Document.from_json(
    json.dumps(
        {
            "target": {
                "id": "dummy_id_12345",
                "url": "http://dummy-url.com/dummy.mp3",
                "type": "Video",
            },
            "creator": {"id": "UNIT TEST", "type": "Organization"},
            "_id": "dummy-uuid-12345-43214",
        }
    )
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


@pytest.mark.parametrize(
    "doc, task, previous_results, save_exception, success",
    [
        (DUMMY_DOC, DUMMY_TASK, [DUMMY_RESULT], None, True),
        (DUMMY_DOC, DUMMY_TASK, [], None, False),
        (DUMMY_DOC, DUMMY_TASK, None, None, False),
        (DUMMY_DOC, DUMMY_TASK, [DUMMY_RESULT], errors.ResultExistsError, False),
        (DUMMY_DOC, DUMMY_TASK, [DUMMY_RESULT], errors.TaskAssignedError, False),
        (DUMMY_DOC, DUMMY_TASK, [], errors.TaskAssignedError, False),
        (DUMMY_DOC, DUMMY_TASK, None, errors.TaskAssignedError, False),
    ],
)
def test_save_prior_download_result(
    config, doc, task, previous_results, save_exception, success
):
    try:
        w = DownloadWorker(config)

        when(w)._get_prior_download_results(doc._id).thenReturn(previous_results)
        when(w)._copy_result(DUMMY_RESULT).thenReturn(DUMMY_RESULT)
        if save_exception is None:
            when(Result).save(task._id).thenReturn()
        else:
            when(Result).save(task._id).thenRaise(save_exception)
        resp = w._save_prior_download_result(doc, task)
        assert resp is success
        verify(w, times=1)._get_prior_download_results(doc._id)

        num_calls_with_prior_results = (
            1 if previous_results and len(previous_results) > 0 else 0
        )
        verify(Result, times=num_calls_with_prior_results).save(task._id)
        verify(w, times=num_calls_with_prior_results)._copy_result(DUMMY_RESULT)
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
        (
            "http://dummy.nl",
            ["nodummy.nl"],
            False,
        ),  # not in whitelist, so should be False
        (
            "http://www.dummy.nl",
            ["dummy.nl"],
            False,
        ),  # www.DOMAIN is not recognized yet
    ],
)
def test_check_whitelist(config, url, whitelist, in_whitelist):
    try:
        w = DownloadWorker(config)
        assert w._check_whitelist(url, whitelist) is in_whitelist
    finally:
        unstub()


@pytest.mark.parametrize(
    "threshold, file_within_threshold, free_disk_space",
    [  # 10MB free disk for most examples
        (10**6, True, 10**7),  # 1MB
        (10**7 - 1, True, 10**7),  # 10MB minus one byte
        (
            10**7,
            False,
            10**7,
        ),  # 10MB is the same as the bytes free, which is not accepted
        (10**8, False, 10**7),  # 100MB
        (10**9, False, 10**7),  # 1GB
        (10**9, True, 10**10),  # 1GB (now 10GB free)
    ],
)
def test_check_download_threshold(
    config, threshold, file_within_threshold, free_disk_space
):
    try:
        w = DownloadWorker(config)
        when(w)._get_bytes_free(DUMMY_DOWNLOAD_DIR).thenReturn(
            free_disk_space
        )  # 10 MB free
        assert (
            w._check_download_threshold(threshold, DUMMY_DOWNLOAD_DIR)
            is file_within_threshold
        )
        verify(w, times=1)._get_bytes_free(DUMMY_DOWNLOAD_DIR)
    finally:
        unstub()


# TODO test with Task.args.PATHS.TEMP_FOLDER (now it is always None)
@pytest.mark.parametrize(
    "doc, task, download_path_exists",
    [
        (DUMMY_DOC, DUMMY_TASK, True),
        (DUMMY_DOC, DUMMY_TASK, False),
    ],
)
def test_determine_download_dir(config, doc, task, download_path_exists):
    try:
        # this part is done by dane.base_classes.getDirs(), recreate it here for transparancy
        dane_dirs = {**DUMMY_DANE_DIRS}
        chunks = os.path.join(
            *[doc._id[i : 2 + i] for i in range(0, min(len(doc._id), 6), 2)]
        )
        dane_dirs["TEMP_FOLDER"] = os.path.join(
            DUMMY_DANE_DIRS["TEMP_FOLDER"], chunks, doc._id
        )
        dane_dirs["OUT_FOLDER"] = os.path.join(
            DUMMY_DANE_DIRS["OUT_FOLDER"], chunks, doc._id
        )

        w = DownloadWorker(config)
        when(w)._generate_dane_dirs_for_doc(doc).thenReturn(
            dane_dirs.get("TEMP_FOLDER", None)
        )
        when(os.path).exists(dane_dirs["TEMP_FOLDER"]).thenReturn(download_path_exists)
        download_dir = w._determine_download_dir(doc, task)
        if download_path_exists:
            assert download_dir == dane_dirs["TEMP_FOLDER"]
        else:
            assert download_dir is None

        verify(w, times=1)._generate_dane_dirs_for_doc(doc)
        verify(os.path, times=1).exists(dane_dirs["TEMP_FOLDER"])
    finally:
        unstub()
