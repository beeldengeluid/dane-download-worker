import sys
import logging
from requests.utils import requote_uri
from urllib.parse import urlparse
import os
from dane.base_classes import base_worker
from dane.config import cfg
from dane import Result, Task, Document
from dane import errors
from base_util import validate_config, parse_file_size, LOG_FORMAT
from s3_download import download_s3_uri
from http_download import download_http
from model import DANEResponse


# initialises the root logger
logging.basicConfig(
    level=cfg.LOGGING.LEVEL,  # this setting has a default in DANE library so safe to use
    stream=sys.stdout,  # configure a stream handler only for now (single handler)
    format=LOG_FORMAT,
)
logger = logging.getLogger()


class DownloadWorker(base_worker):
    # we specify a queue name because every worker of this type should
    # listen to the same queue
    __queue_name = "DOWNLOAD"

    def __init__(self, config):
        logger.debug(config)

        self.UNIT_TESTING = os.getenv("DW_DOWNLOAD_UNIT_TESTING", False)

        if not validate_config(config, not self.UNIT_TESTING):
            logger.error("Invalid config, quitting")
            quit()

        self.whitelist = config.DOWNLOADER.WHITELIST
        self.threshold = None
        if "FS_THRESHOLD" in config.DOWNLOADER.keys():
            # in bytes, might only work on Unix
            self.threshold = parse_file_size(config.DOWNLOADER.FS_THRESHOLD)

        super().__init__(
            queue=self.__queue_name,
            binding_key="#.DOWNLOAD",
            config=config,
            auto_connect=not self.UNIT_TESTING,
            no_api=self.UNIT_TESTING,
        )

    def callback(self, task, doc):  # noqa: C901 #TODO
        # encode the URI, make sure it's safe
        target_url = requote_uri(doc.target["url"])
        is_s3 = self._is_s3_uri(target_url)
        logger.info(f"Download task for: {target_url}")

        # check the white list in case it's not an S3 URI
        if not is_s3:
            if not self._check_whitelist(target_url, self.whitelist):
                return DANEResponse(
                    403, f"Source url not in whitelist: {target_url}"
                ).to_json()

        # define the download/temp dir by checking task arguments and default DANE config
        download_dir = self._determine_download_dir(doc, task)

        # only continue if the dir is accessible by this dane-download-worker
        if download_dir is None:
            logger.error(f"Download dir does not exist: {download_dir}")
            return DANEResponse(
                500, "Non existing TEMP_FOLDER, cannot handle request"
            ).to_json()

        # check if the file fits the download threshhold
        if not self._check_download_threshold(self.threshold, download_dir):
            logger.error("Insufficient disk space")
            raise errors.RefuseJobException("Insufficient disk space")

        # call the correct downloader
        if is_s3:
            result = download_s3_uri(target_url, download_dir)
        else:
            result = download_http(target_url, download_dir)

        dane_result_saved = False
        if result.already_downloaded:  # TODO or result.dane_result.state == 201
            logger.info("File was already downloaded, trying to save prior DANE result")
            dane_result_saved = self._save_prior_download_result(doc, task)

        # in case of no error go ahead with writing the DANE Result
        if result.dane_response.state == 200 and not dane_result_saved:
            r = Result(
                self.generator,
                payload={
                    "file_path": result.download_file_path,  # TODO extract file info from the file
                    **result.file_info,  # add any extracted file info
                },
                api=self.handler,
            )
            r.save(task._id)
            logger.debug(f"Succesfully downloaded: {target_url}")
            return result.dane_response.to_json()

        # it must be an error, return it to DANE
        return result.dane_response.to_json()

    # try to copy the DANE Result for a possibly earlier download
    def _save_prior_download_result(self, doc: Document, task: Task) -> bool:
        try:
            results = self._get_prior_download_results(doc._id)
            if results and len(results) > 0:
                # arbitrarly choose the first one to copy, perhaps should have some
                # timestamp mechanism..
                r = self._copy_result(results[0])
                r.save(task._id)
                logger.info("Successfully saved result for task: {}".format(task._id))
                return True
        except (errors.ResultExistsError, errors.TaskAssignedError):
            # seems the tasks or results no longer exists
            # just redownload and get fresh info
            logger.info(
                "Redownloading anyway, since prior result data could not be retrieved: {}".format(
                    task._id
                )
            )
        return False

    def _get_prior_download_results(
        self, doc_id: str
    ) -> list:  # list with Result objects
        return self.handler.searchResult(doc_id, "DOWNLOAD")

    def _copy_result(self, result: Result) -> Result:
        return Result(self.generator, payload=result.payload, api=self.handler)

    def _get_bytes_free(self, download_dir: str) -> int:
        disk_stats = os.statvfs(download_dir)
        return disk_stats.f_frsize * disk_stats.f_bfree

    def _check_download_threshold(self, threshold: int, download_dir: str) -> bool:
        if threshold is not None:
            bytes_free = self._get_bytes_free(download_dir)
            if bytes_free <= threshold:
                return False
        return True

    def _check_whitelist(self, target_url: str, whitelist: list) -> bool:
        parse = urlparse(target_url)
        if parse.netloc not in whitelist:
            logger.warning(
                "Requested URL Not in whitelist: {}".format("; ".join(whitelist))
            )
            return False
        return True

    # returns this "chunked" dir based on the doc id
    # (see dane.base_classes.getDirs())
    def _generate_dane_dirs_for_doc(self, doc: Document) -> dict:
        return self.getDirs(doc).get("TEMP_FOLDER", None)

    def _determine_download_dir(self, doc: Document, task: Task) -> str:
        download_dir = task.args.get("PATHS", {}).get("TEMP_FOLDER", None)

        # use the provided Task.args.PATHS.TEMP_FOLDER if it exists,
        # otherwise generate a new path
        if download_dir is None or os.path.exists(download_dir) is False:
            download_dir = self._generate_dane_dirs_for_doc(doc)
        return download_dir if download_dir and os.path.exists(download_dir) else None

    def _is_s3_uri(self, uri):
        return type(uri) == str and urlparse(uri).scheme == "s3"


if __name__ == "__main__":
    dlw = DownloadWorker(cfg)
    logging.debug(" # Initialising worker. Ctrl+C to exit")
    try:
        dlw.run()
    except (KeyboardInterrupt, SystemExit):
        dlw.stop()
