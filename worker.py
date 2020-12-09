import json
import urllib.request as req
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from requests.utils import requote_uri
import shutil
import os

import DANE.base_classes
from DANE.config import cfg
from DANE import Result
from DANE import errors


def parseSize(size, units = 
        {"B": 1, "KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}):
    """Human readable size to bytes"""

    if not ' ' in size:
        # no space in size, assume last 2 char are unit
        size = size[:-2] + ' ' + size[-2:]

    number, unit = [string.strip() for string in size.upper().split()]
    return int(float(number)*units[unit])

class download_worker(DANE.base_classes.base_worker):
    # we specify a queue name because every worker of this type should 
    # listen to the same queue
    __queue_name = 'DOWNLOAD'

    def __init__(self, config):
        super().__init__(queue=self.__queue_name, 
                binding_key='#.DOWNLOAD', config=config)

        self.whitelist = config.DOWNLOADER.WHITELIST

        self.threshold = None
        if 'FS_THRESHOLD' in config.DOWNLOADER.keys():
            # in bytes, might only work on Unix
            self.threshold = parseSize(config.DOWNLOADER.FS_THRESHOLD)

    def callback(self, task, doc):
        target_url = requote_uri(doc.target['url'])
        parse = urlparse(target_url)
        if parse.netloc not in self.whitelist:
            return {'state': 403, 
                'message': 'Source url not permitted'}

        if 'PATHS' not in task.args.keys() or \
                'TEMP_FOLDER' not in task.args['PATHS'].keys():
            task.args['PATHS'] = task.args.get('PATHS', {})
            task.args['PATHS'].update(self.getDirs(doc))

        temp_dir = task.args['PATHS']['TEMP_FOLDER']
        if not os.path.exists(temp_dir):
            #TODO find better error no.
            return {'state': 500, 
                'message': "Non existing TEMP_FOLDER, cannot handle request"}

        if self.threshold is not None:
            # check if there is enough disk space to do something meaningful
            disk_stats = os.statvfs(temp_dir)
            bytes_free = disk_stats.f_frsize * disk_stats.f_bfree 
            if bytes_free <= self.threshold:
                #  There isnt. Refuse and requeue for now
                raise DANE.errors.RefuseJobException('Insufficient disk space')

        fn = os.path.basename(parse.path)
        file_path = os.path.join(temp_dir, fn)

        if os.path.exists(file_path):
            # source file already downloaded
            # try to find that result so we can copy download info 
            try:
                possibles = self.handler.searchResult(doc._id, 'DOWNLOAD')
                if len(possibles) > 0:
                    # arbitrarly choose the first one to copy, perhaps should have some
                    # timestamp mechanism..

                    r = Result(self.generator, payload=possibles[0].payload,
                            api=self.handler)
                    r.save(task._id)

                    return {'state': 200, 'message': 'Success'}
            except errors.ResultExistsError, errors.TaskAssignedError:
                # seems the tasks or results no longer exists
                # just redownload and get fresh info
                pass

        try:
            with req.urlopen(target_url) as response, \
                    open(file_path, 'wb') as out_file:
                headers = response.info()
                # TODO could use content-disposition to rename file
                # does require some parsing of
                # headers.get_content_disposition()
                shutil.copyfileobj(response, out_file)
                out_size = out_file.tell()

            content_length = int(headers.get('Content-Length', failobj=-1))
            if content_length > -1 and out_size != content_length:
                return json.dumps({'state': 502, 
                    'message': "Received incomplete file: " +
                        "{} ({} out of {} bytes)".format(fn, out_size, 
                            content_length)})
        except HTTPError as e:
            if e.code == 404:
                return {'state': e.code, 
                    'message': e.reason}
            elif e.code == 500:
                return {'state': 503, 
                    'message': "Source host 500 error: " + e.reason}
            else:
                return {'state': 500, 
                    'message': "Unhandled source host error: "
                            + str(e.code) + " " + e.reason}
        else:
            # TODO filter for allowed content-types?
            c_type = headers.get_content_type()
            if '/' in c_type:
                file_type = c_type.split('/')[0]
            else:
                # TODO logs this, as idk when this would occur
                # and potentially can just pass entire c_type on then
                file_type = 'unknown'

            r = Result(self.generator, payload={
                'file_path': file_path,
                'file_type': file_type, 
                'Content-Type': c_type,
                'Content-Length': content_length
                }, api=self.handler)
            r.save(task._id)

            return {'state': 200, 'message': 'Success'} 

if __name__ == '__main__':

    dlw = download_worker(cfg)

    print(' # Initialising worker. Ctrl+C to exit')
    try: 
        dlw.run()
    except (KeyboardInterrupt, SystemExit):
        dlw.stop()
