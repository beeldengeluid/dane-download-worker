import json
import urllib.request as req
from urllib.error import HTTPError
from urllib.parse import urlparse, unquote
from requests.utils import requote_uri
import shutil
import os
import unicodedata
import DANE.base_classes
from DANE.config import cfg
from DANE import Result
from DANE import errors
import string
import uuid
from base_util import init_logger, validate_config


def parse_file_size(
    size, units={"B": 1, "KB": 10 ** 3, "MB": 10 ** 6, "GB": 10 ** 9, "TB": 10 ** 12}
):
    if " " not in size:
        # no space in size, assume last 2 char are unit
        size = size[:-2] + " " + size[-2:]

    number, unit = [s.strip() for s in size.upper().split()]
    return int(float(number) * units[unit])


valid_filename_chars = "-_. {}{}".format(string.ascii_letters, string.digits)


class DownloadWorker(DANE.base_classes.base_worker):
    # we specify a queue name because every worker of this type should
    # listen to the same queue
    __queue_name = "DOWNLOAD"

    def __init__(self, config):
        self.logger = init_logger(config)
        self.logger.debug(config)

        self.UNIT_TESTING = os.getenv("BG_DL_PROXY_UNIT_TESTING", False)

        if not validate_config(config, not self.UNIT_TESTING):
            self.logger.error("Invalid config, quitting")
            quit()

        self.whitelist = config.DOWNLOADER.WHITELIST
        self.threshold = None
        if "FS_THRESHOLD" in config.DOWNLOADER.keys():
            # in bytes, might only work on Unix
            self.threshold = parse_file_size(config.DOWNLOADER.FS_THRESHOLD)

        super().__init__(
            queue=self.__queue_name, binding_key="#.DOWNLOAD", config=config
        )

    # makes sure any URL is downloaded to a file with an OS friendly file name (that still is human readable)
    def __url_to_safe_filename(
        self, url, whitelist=valid_filename_chars, replace=" ", char_limit=255
    ):
        # ; in the url is terrible, since it cuts off everything after the ; when running urlparse
        url = url.replace(";", "")

        # grab the url path
        url_path = urlparse(url).path

        # get the file/dir name from the URL (if any)
        url_file_name = os.path.basename(url_path)

        # also make sure to get rid of the URL encoding
        filename = unquote(url_file_name if url_file_name != "" else url_path)

        # if both the url_path and url_file_name are empty the filename will be meaningless, so then assign a random UUID
        filename = str(uuid.uuid4()) if filename in ["", "/"] else filename

        # replace spaces (or anything else passed in the replace param) with underscores
        for r in replace:
            filename = filename.replace(r, "_")

        # keep only valid ascii chars
        cleaned_filename = (
            unicodedata.normalize("NFKD", filename).encode("ASCII", "ignore").decode()
        )

        # keep only whitelisted chars
        cleaned_filename = "".join(c for c in cleaned_filename if c in whitelist)
        if len(cleaned_filename) > char_limit:
            self.logger.warning(
                "Warning, filename truncated because it was over {}. Filenames may no longer be unique".format(
                    char_limit
                )
            )
        return cleaned_filename[:char_limit]

    def __requires_download(self, doc, task, download_file_path):
        if os.path.exists(download_file_path):
            self.logger.debug("Already downloaded {}".format(download_file_path))
            return self.__save_prior_download_result(doc, task) is False
        return True

    # try to copy the DANE Result for a possibly earlier download
    def __save_prior_download_result(self, doc, task):
        try:
            possibles = self.handler.searchResult(doc._id, "DOWNLOAD")
            if len(possibles) > 0:
                # arbitrarly choose the first one to copy, perhaps should have some
                # timestamp mechanism..

                r = Result(
                    self.generator, payload=possibles[0].payload, api=self.handler
                )
                r.save(task._id)
                self.logger.debug(
                    "Successfully saved result for task: {}".format(task._id)
                )
                return True
        except (errors.ResultExistsError, errors.TaskAssignedError):
            # seems the tasks or results no longer exists
            # just redownload and get fresh info
            self.logger.debug(
                "Redownloading anyway, since prior result data could not be retrieved: {}".format(
                    task._id
                )
            )
        return False

    def __check_download_threshold(self, threshold, download_dir):
        if threshold is not None:
            disk_stats = os.statvfs(download_dir)
            bytes_free = disk_stats.f_frsize * disk_stats.f_bfree
            if bytes_free <= threshold:
                return False
        return True

    def __check_whitelist(self, target_url, whitelist):
        parse = urlparse(target_url)
        if parse.netloc not in whitelist:
            self.logger.warning(
                "Requested URL Not in whitelist: {}".format("; ".join(whitelist))
            )
            return False
        return True

    def __determine_download_dir(self, doc, task):
        if (
            "PATHS" not in task.args.keys()
            or "TEMP_FOLDER" not in task.args["PATHS"].keys()
        ):
            task.args["PATHS"] = task.args.get("PATHS", {})
            task.args["PATHS"].update(
                self.getDirs(doc)
            )  # returns this "chunked" dir based on the doc id
        download_dir = task.args["PATHS"]["TEMP_FOLDER"]
        return download_dir if os.path.exists(download_dir) else None

    def callback(self, task, doc):
        # encode the URI, make sure it's safe
        target_url = requote_uri(doc.target["url"])
        self.logger.debug("Download task for: {}".format(target_url))

        # check the white list to see if the URL can be downloaded
        if not self.__check_whitelist(target_url, self.whitelist):
            return {"state": 403, "message": "Source url not permitted"}

        # define the download/temp dir by checking task arguments and default DANE config
        download_dir = self.__determine_download_dir(doc, task)

        # only continue if the dir is accessible by this dane-download-worker
        if download_dir is None:
            self.logger.error("Download dir does not exist: {}".format(download_dir))
            return {
                "state": 500,
                "message": "Non existing TEMP_FOLDER, cannot handle request",
            }

        # check if the file fits the download threshhold
        if not self.__check_download_threshold(self.threshold, download_dir):
            self.logger.error("Insufficient disk space")
            raise DANE.errors.RefuseJobException("Insufficient disk space")

        download_filename = self.__url_to_safe_filename(target_url)
        download_file_path = os.path.join(download_dir, download_filename)

        # maybe the file was already downloaded
        if not self.__requires_download(doc, task, download_file_path):
            return {"state": 200, "message": "Success"}

        # now proceed to the actual downloading and saving the download result
        try:
            with req.urlopen(target_url) as response, open(
                download_file_path, "wb"
            ) as out_file:
                headers = response.info()
                shutil.copyfileobj(response, out_file)
                out_size = out_file.tell()

            content_length = int(headers.get("Content-Length", failobj=-1))
            if content_length > -1 and out_size != content_length:
                self.logger.warning(
                    "Download incomplete for: {}".format(download_filename)
                )
                return json.dumps(
                    {
                        "state": 502,
                        "message": "Received incomplete file: {} ({} out of {} bytes)".format(
                            download_filename, out_size, content_length
                        ),
                    }
                )
        except HTTPError as e:
            if e.code == 404:
                self.logger.warning("Source returned 404: {}".format(e.reason))
                return {"state": e.code, "message": e.reason}
            elif e.code == 500:
                self.logger.warning("Source returned 500: {}".format(e.reason))
                return {"state": 503, "message": "Source host 500 error: " + e.reason}
            else:
                self.logger.warning(
                    "Source returned an unknown error: {}".format(e.reason)
                )
                return {
                    "state": 500,
                    "message": "Unhandled source host error: "
                    + str(e.code)
                    + " "
                    + e.reason,
                }
        else:  # means the download was successful, time to write the result to ES and return a response
            c_type = (
                headers.get_content_type()
            )  # TODO filter for allowed content-types?
            if "/" in c_type:
                file_type = c_type.split("/")[0]
            else:
                self.logger.warning("Handling unknown file type: {}".format(c_type))
                file_type = "unknown"

            r = Result(
                self.generator,
                payload={
                    "file_path": download_file_path,
                    "file_type": file_type,
                    "Content-Type": c_type,
                    "Content-Length": content_length,
                },
                api=self.handler,
            )
            r.save(task._id)
            self.logger.debug("Succesfully downloaded: {}".format(target_url))
            return {"state": 200, "message": "Success"}


if __name__ == "__main__":

    dlw = DownloadWorker(cfg)

    print(" # Initialising worker. Ctrl+C to exit")
    try:
        dlw.run()
    except (KeyboardInterrupt, SystemExit):
        dlw.stop()
