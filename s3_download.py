import logging
import boto3
import os
from typing import Tuple
from model import DownloadResult, DANEResponse


logger = logging.getLogger(__name__)


# e.g. s3://bucket/subdir/filename
def deconstruct_s3_uri(s3_uri: str) -> Tuple[str, str, str]:
    tmp = s3_uri[5:]
    return (
        tmp[0 : tmp.find("/")],
        tmp[tmp.find("/") + 1 :],
        tmp[tmp.rfind("/") + 1 :],
    )


# https://stackoverflow.com/questions/57280767/s3-an-error-occurred-403-when-calling-the-headobject-operation-forbidden
# https://stackoverflow.com/questions/36144757/aws-cli-s3-a-client-error-403-occurred-when-calling-the-headobject-operation
def download_s3_uri(s3_uri: str, download_dir: str) -> DownloadResult:
    logger.info(s3_uri)
    s3 = boto3.client("s3")
    bucket, key, fn = deconstruct_s3_uri(s3_uri)
    download_file_path = os.path.join(download_dir, fn)

    # first check if the file was already downloaded
    if os.path.exists(download_file_path):
        return DownloadResult(
            download_file_path,
            DANEResponse(200, f"{download_file_path} was already downloaded"),
            True,
            {},  # no file_info
        )

    # go ahead with the download
    try:
        with open(download_file_path, "wb") as f:
            s3.download_fileobj(bucket, key, f)
            logger.info("download done")
        return DownloadResult(
            download_file_path,
            DANEResponse(200, "Success"),
            False,
            {},  # TODO try to extract some file info
        )
    except Exception as e:
        logger.exception(f"Error while downloading {s3_uri}")
        return DownloadResult(
            download_file_path,
            DANEResponse(500, f"Unkown error: {str(e)}"),
            False,
            {},  # no file info in case of an error
        )
