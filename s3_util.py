import logging
import boto3
import os
from typing import Tuple


logger = logging.getLogger(__name__)


# e.g. s3://bucket/subdir/filename
def deconstruct_s3_uri(s3_uri: str) -> Tuple[str, str, str]:
    tmp = s3_uri[5:]
    return (
        tmp[0 : tmp.find("/")],
        tmp[tmp.find("/") + 1 :],
        tmp[tmp.rfind("/") + 1 :],
    )


def download_s3_uri(s3_uri: str, download_dir: str, access_key: str, secret: str):
    logger.info(s3_uri)
    s3 = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret)
    bucket, key, fn = deconstruct_s3_uri(s3_uri)
    try:
        with open(os.path.join(download_dir, fn), "wb") as f:
            s3.download_fileobj(bucket, key, f)
            logger.info("download done")
        return True
    except Exception:
        logger.exception(f"Error while downloading {s3_uri}")
    return False
