import logging
import os
from urllib.parse import unquote
from urllib3.response import HTTPResponse
from requests import Response

logger = logging.getLogger(__name__)


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
