import logging
import boto3
import os
from typing import Tuple
from model import DownloadResult, DANEResponse


logger = logging.getLogger(__name__)


def validate_s3_uri(s3_uri: str) -> bool:
    if "s3://" not in s3_uri:
        logger.error(f"S3 URI without protocol: {s3_uri}")
        return False

    tmp = s3_uri[5:].split("/")
    if len(tmp) < 2:
        logger.error(f"S3 URI must have a bucket name and a file name: {s3_uri}")
        return False
    logger.info(f"S3 URI seems valid: {s3_uri}")
    return True


# e.g. s3://bucket/subdir/filename OR s3://bucket/filename
def deconstruct_s3_uri(s3_uri: str) -> Tuple[str, str, str]:
    tmp = s3_uri[5:]  # bucket/subdir/filename
    return (
        tmp[0 : tmp.find("/")],  # bucket
        tmp[tmp.find("/") + 1 :],  # subdir/filename OR filename
        tmp[tmp.rfind("/") + 1 :],  # filename
    )


# https://stackoverflow.com/questions/57280767/s3-an-error-occurred-403-when-calling-the-headobject-operation-forbidden
# https://stackoverflow.com/questions/36144757/aws-cli-s3-a-client-error-403-occurred-when-calling-the-headobject-operation
def download_s3_uri(s3_uri: str, download_dir: str) -> DownloadResult:
    logger.info(f"Attempting to download {s3_uri}")

    # first validate the s3_uri
    if not validate_s3_uri(s3_uri):
        return DownloadResult(
            "",  # no download_file_path available
            DANEResponse(400, f"Invalid S3 URI: {s3_uri}"),
            False,
            {},  # no file info in case of an error
        )

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
        if os.path.exists(download_file_path):
            logger.info("Deleting corrupt/empty file due to failed download")
            os.remove(download_file_path)
        return DownloadResult(
            download_file_path,
            DANEResponse(500, f"Unkown error: {str(e)}"),
            False,
            {},  # no file info in case of an error
        )
