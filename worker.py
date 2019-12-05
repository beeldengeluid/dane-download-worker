from DANE_utils.base_classes import base_worker
import json
import settings
from urllib.parse import urlparse
import urllib.request as req
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
        local_fn, headers = req.urlretrieve(job.source_url, file_path)

        print("fn", local_fn)
        print("headers", headers)

        return json.dumps({'state': 200, 
            'message': 'Success', 
            'file_path': file_path})

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
    except KeyboardInterrupt:
        dlw.stop()
