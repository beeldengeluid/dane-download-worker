import logging
import os
import requests
import unicodedata
import uuid
import string
from urllib.parse import unquote, urlparse
from urllib3.response import HTTPResponse
from requests import Response

logger = logging.getLogger(__name__)
VALID_FILENAME_CHARS = "-_. {}{}".format(string.ascii_letters, string.digits)


def determine_url_extension(url: str):
    return determine_stream_extension(requests.head(url))


# determine the file extension of the requested content via Content-Type and Content-Disposition
def determine_stream_extension(http_resp: HTTPResponse | Response) -> str:
    logging.info("Determining stream extension from http headers")
    content_type = http_resp.headers.get("Content-Type", "")
    content_disposition = http_resp.headers.get("Content-Disposition", "")
    logging.info(
        f"Content-Type: {content_type}; Content-Disposition: {content_disposition}"
    )

    # try to extract the extension from the content_disposition
    ext = extract_extension_from_content_disposition(content_disposition)
    if ext:
        return ext

    logging.info(f"Determine extension based on mime_type {content_type}")
    # try to determine the extension based on the mime_type (taken from Content-Type)
    # TODO this could be done much more completely with a good mime_type lib
    if content_type.find("video/mp4") != -1:
        ext = ".mp4"
    elif content_type.find("video/x-msvideo") != -1:
        ext = ".avi"
    elif content_type.find("video/x-ms-wmv") != -1:
        ext = ".wmv"
    elif content_type.find("audio/mpeg") != -1:
        ext = ".mp3"
    elif content_type.find("audio/wav") != -1:
        ext = ".wav"
    elif content_type.find("audio/midi") != -1:
        ext = ".mid"
    elif content_type.find("application/mxf") != -1:
        ext = ".mxf"
    elif content_type.find("text/html") != -1:
        ext = ".html"
    else:
        logging.warning(f"No supported extension found! (content_type={content_type})")
        return ""

    return ext


# see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition
# see: https://datatracker.ietf.org/doc/html/rfc5987
# NOTE: not nice, but works for now.
# NOTE: possibly replace with https://pypi.org/project/content-disposition/
def extract_extension_from_content_disposition(content_disposition: str) -> str:
    logging.info(
        f"Determine extension based on content disposition {content_disposition}"
    )
    if not content_disposition:
        return ""

    arr = content_disposition.split(";")
    for x in arr:
        if "filename=" in x:
            # strip leading/trailing whitespaces, double quotes and return the bit past the =
            f = x.strip()[len("filename=") :].replace('"', "")
            fn, ext = os.path.splitext(f)  # extract the file extension
            return ext
        elif "filename*=" in x:
            f = x.strip()[x.rfind("'") :].replace('"', "")
            decoded_f = unquote(f)
            fn, ext = os.path.splitext(decoded_f)  # extract the file extension
            return ext
    return ""


def url_to_output_filename(target_url: str) -> str:
    download_filename = url_to_safe_filename(target_url)
    fn, ext = os.path.splitext(download_filename)
    if not ext:
        logger.info("No extension in URL, determining extension with HEAD request")
        extension = determine_url_extension(target_url)  # includes .
        download_filename += f"{extension}"

    return download_filename


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
