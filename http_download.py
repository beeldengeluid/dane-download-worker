import os
import string
import unicodedata
import uuid
import logging
import urllib.request as req
from urllib.parse import urlparse, unquote
from urllib.error import HTTPError
import shutil
from model import DownloadResult, DANEResponse


logger = logging.getLogger(__name__)
VALID_FILENAME_CHARS = "-_. {}{}".format(string.ascii_letters, string.digits)


def download_http(target_url, download_dir) -> DownloadResult:
    download_filename = url_to_safe_filename(target_url)
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


def url_to_safe_filename(url: str) -> str:
    prepped_url = preprocess_url(url)
    if not prepped_url:
        return ""

    unsafe_fn = extract_filename_from_url(prepped_url)

    return to_safe_filename(unsafe_fn)


def preprocess_url(url: str) -> str:
    if type(url) != str:
        return ""

    # ; in the url is terrible, since it cuts off everything after the ; when running urlparse
    url = url.replace(";", "")

    # make sure to get rid of the URL encoding
    return unquote(url)


def extract_filename_from_url(url: str) -> str:
    if type(url) != str:
        return ""

    # grab the url path
    url_path = urlparse(url).path
    if url_path.rfind("/") == len(url_path) - 1:
        url_path = url_path[:-1]
    url_host = urlparse(url).netloc

    # get the file/dir name from the URL (if any)
    fn = os.path.basename(url_path)

    # if the url_path is empty, the file name is meaningless, so return a string based on the url_host
    return (
        f"{url_host.replace('.', '_')}__{str(uuid.uuid4())}" if fn in ["", "/"] else fn
    )


def to_safe_filename(
    fn: str, whitelist: str = VALID_FILENAME_CHARS, char_limit: int = 255
) -> str:
    if not fn:
        return ""

    # replace spaces with underscore (spaces in filenames aren't nice)
    fn = fn.replace(" ", "_")

    safe_fn = unicodedata.normalize("NFKD", fn).encode("ASCII", "ignore").decode()

    # keep only whitelisted chars
    safe_fn = "".join(c for c in safe_fn if c in whitelist)

    if len(safe_fn) > char_limit:
        print(
            "Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(
                char_limit
            )
        )
    return safe_fn[:char_limit]
