import json
import settings
from urllib.parse import urlparse
import urllib.request as req
from urllib.error import HTTPError
from urllib.parse import urljoin
import shutil
import os

import DANE.base_classes


def parseSize(size, units = 
        {"B": 1, "KB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}):
    """Human readable size to bytes"""

    number, unit = [string.strip() for string in size.upper().split()]
    return int(float(number)*units[unit])

class download_worker(DANE.base_classes.base_worker):
    # we specify a queue name because every worker of this type should 
    # listen to the same queue
    __queue_name = 'DOWNLOAD'

    def __init__(self, whitelist, config):
        super().__init__(queue=self.__queue_name, 
                binding_key='#.DOWNLOAD', config=config)

        self.whitelist = whitelist
        self.search_api = urljoin(config['API'], 'job/search/{}')
        self.job_api = urljoin(config['API'], 'job/{}')

    def callback(self, job):
        parse = urlparse(job.source_url)
        if parse.netloc not in self.whitelist:
            return json.dumps({'state': 403, 
                'message': 'Source url not permitted'})

        if 'SHARED' not in job.response.keys() or \
                'TEMP_FOLDER' not in job.response['SHARED'].keys():
            #TODO find better error no.
            return json.dumps({'state': 500, 
                'message': "TEMP_FOLDER not specified, cannot handle request"})

        temp_dir = job.response['SHARED']['TEMP_FOLDER']
        if not os.path.exists(temp_dir):
            #TODO find better error no.
            return json.dumps({'state': 500, 
                'message': "Non existing TEMP_FOLDER, cannot handle request"})

        if 'FS_THRESHOLD' in self.config.keys():
            thres_bytes = parseSize(self.config['FS_THRESHOLD'])
            # this might be Unix only
            # check if there is enough disk space, to do something meaningful
            disk_stats = os.statvfs(temp_dir)
            bytes_free = statvfs.f_frsize * statvfs.f_bfree 
            if bytes_free <= thres_bytes:
                # Refuse and requeue for now
                raise DANE.errors.RefuseJobException('Insufficient disk space')

        fn = os.path.basename(parse.path)
        file_path = os.path.join(temp_dir, fn)

        if os.path.exists(file_path):
            # source file already downloaded
            # figure out which job it was
            try:
                r = req.urlopen(self.search_api.format(job.source_id))
                txt = r.read().decode(r.headers.get_content_charset(
                        failobj="utf-8"))
                jobs = json.loads(txt)['jobs']

                for j in jobs:
                    if j != job.job_id:
                        r = req.urlopen(self.job_api.format(j))
                        txt = r.read().decode(r.headers.get_content_charset(
                                failobj="utf-8"))
                        jb = jobspec.from_json(txt)
                        if 'DOWNLOAD' in jb.response.keys():
                            # and copy information from that job
                            resp = jb.response['DOWNLOAD']
                            return json.dumps({'state': 200, 
                                'message': 'Success', **resp})
            except HTTPError as e:
                if e.code == 404:
                    return json.dumps({'state': e.code, 
                        'message': e.reason})
                elif e.code == 500:
                    return json.dumps({'state': 503, 
                        'message': "Source host 500 error: " + e.reason})
                else:
                    return json.dumps({'state': 500, 
                        'message': "Unhandled source host error: "
                                + str(e.code) + " " + e.reason})

        try:
            with req.urlopen(job.source_url) as response, \
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
                return json.dumps({'state': e.code, 
                    'message': e.reason})
            elif e.code == 500:
                return json.dumps({'state': 503, 
                    'message': "Source host 500 error: " + e.reason})
            else:
                return json.dumps({'state': 500, 
                    'message': "Unhandled source host error: "
                            + str(e.code) + " " + e.reason})
        else:
            # TODO filter for allowed content-types?
            c_type = headers.get_content_type()
            if '/' in c_type:
                file_type = c_type.split('/')[0]
            else:
                # TODO logs this, as idk when this would occur
                # and potentially can just pass entire c_type on then
                file_type = 'unknown'

            return json.dumps({'state': 200, 
                'message': 'Success', 
                'file_path': file_path,
                'file_type': file_type, 
                'Content-Type': c_type,
                'Content-Length': content_length})

if __name__ == '__main__':
    config = settings.config
    rconfig = config['RABBITMQ']

    dlw = download_worker(config['WHITELIST'], config)

    print(' # Initialising worker. Ctrl+C to exit')
    try: 
        dlw.run()
    except (KeyboardInterrupt, SystemExit):
        dlw.stop()
