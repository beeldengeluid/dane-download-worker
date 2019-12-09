from DANE_utils.base_classes import base_worker
import json
import settings
from urllib.parse import urlparse
import urllib.request as req
from urllib.error import HTTPError
import shutil
import os

class download_worker(base_worker):
    # we specify a queue name because every worker of this type should 
    # listen to the same queue
    __queue_name = 'DOWNLOAD'

    def __init__(self, whitelist, out_dir, host, exchange='DANE-exchange', 
            port=5672, user='guest', password='guest'):
        super().__init__(host=host, queue=self.__queue_name, 
                binding_key='#.DOWNLOAD', port=port, user=user, password=password)

        self.whitelist = whitelist
        self.out_dir = out_dir

    def callback(self, job):
        parse = urlparse(job.source_url)
        if parse.netloc not in self.whitelist:
            return json.dumps({'state': 403, 
                'message': 'Source url not permitted'})

        fn = os.path.basename(parse.path)

        # TODO store in smaller subdirs
        dir_path = os.path.join(self.out_dir, job.source_set, job.source_id)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        file_path = os.path.join(dir_path, fn)
        try:
            with req.urlopen(job.source_url) as response, \
                    open(file_path, 'wb') as out_file:
                headers = response.info()
                # TODO could use content-disposition to rename file
                # does require some parsing of
                # headers.get_content_disposition()
                shutil.copyfileobj(response, out_file)
                out_size = out_file.tell()

            content_length = int(headers.get('Content-Length'))
            if out_size != content_length:
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
                # and potentially can just pass c_type on then
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

    dlw = download_worker(config['WHITELIST'],
            config['IN_FOLDER'],
            host=rconfig['host'],
            port=rconfig['port'],
            exchange=rconfig['exchange'],
            user=rconfig['user'],
            password=rconfig['password'])

    print(' # Initialising worker. Ctrl+C to exit')
    try: 
        dlw.run()
    except (KeyboardInterrupt, SystemExit):
        dlw.stop()
