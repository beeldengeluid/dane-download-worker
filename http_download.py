import os
import logging
import urllib.request as req
from urllib.error import HTTPError
import shutil
from model import DownloadResult, DANEResponse
from http_util import url_to_output_filename


logger = logging.getLogger(__name__)


def download_http(target_url, download_dir) -> DownloadResult:
    download_filename = url_to_output_filename(target_url)
    download_file_path = os.path.join(download_dir, download_filename)
    # first check if the file was already downloaded
    if os.path.exists(download_file_path):
        return DownloadResult(
            download_file_path,
            DANEResponse(201, f"{download_file_path} was already downloaded"),
            True,
            {},  # no file_info
        )

    already_downloaded = False
    dane_response = None
    file_info = {}

    # try to download
    try:
        with req.urlopen(target_url) as response, open(
            download_file_path, "wb"
        ) as out_file:
            headers = response.info()
            shutil.copyfileobj(response, out_file)
            out_size = out_file.tell()

        content_length = int(headers.get("Content-Length", failobj=-1))
        if content_length > -1 and out_size != content_length:
            logger.warning("Download incomplete for: {}".format(download_filename))
            dane_response = DANEResponse(
                502,
                "Received incomplete file: {} ({} out of {} bytes)".format(
                    download_filename, out_size, content_length
                ),
            )

    except HTTPError as e:
        error_msg = f"Unkown {e.code} error: {e.reason}"
        if e.code == 404:
            error_msg = f"Source returned 404: {e.reason}"
            dane_response = DANEResponse(404, e.reason)
        elif e.code == 500:
            error_msg = f"Source returned 500: {e.reason}"
            dane_response = DANEResponse(503, error_msg)  # set to 503
        else:
            dane_response = DANEResponse(500, error_msg)
        logger.warning(error_msg)
    else:
        # download was successful, try to extract the file info from the headers
        file_info = extract_file_info(headers)
        dane_response = DANEResponse(200, "Success")

    return DownloadResult(
        download_file_path, dane_response, already_downloaded, file_info
    )


def extract_file_info(resp_headers):
    content_length = int(resp_headers.get("Content-Length", failobj=-1))
    c_type = resp_headers.get_content_type()  # TODO filter for allowed content-types?
    if "/" in c_type:
        file_type = c_type.split("/")[0]
    else:
        logger.warning("Handling unknown file type: {}".format(c_type))
        file_type = "unknown"
    return {
        "file_type": file_type,
        "Content-Type": c_type,
        "Content-Length": content_length,
    }
