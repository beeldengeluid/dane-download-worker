import pika
import uuid
import json

from DANE_utils import jobspec
import settings

class dl_server():

    def __init__(self):
        config = settings.config['RABBITMQ']
        self.config = config

        credentials = pika.PlainCredentials(config['user'],
            config['password'])
        self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        credentials=credentials,
                        host=config['host'], port=config['port']))

        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='response_queue', exclusive=True)

        self.channel.basic_consume(
            queue='response_queue',
            on_message_callback=self.on_response,
            auto_ack=True)

    def on_response(self, ch, method, props, body):
        print('# Response:', json.loads(body))
        self.stop()
        print('## Handled response. Exiting..')

    def run(self):
        self.channel.start_consuming()

    def stop(self):
        self.channel.stop_consuming()

    def simulate_request(self):
        job = jobspec.jobspec(source_url='http://prd-app-bng-01.beeldengeluid.nl:8093/viz/NETWERK______-WON00531377', 
            source_id='ITM123', source_set='NISVtest',
            tasks=jobspec.taskSequential(['DOWNLOAD', 'TEST']))

        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange=self.config['exchange'],
            routing_key='DOWNLOAD',
            properties=pika.BasicProperties(
                reply_to='response_queue',
                correlation_id=self.corr_id,
            ),
            body=job.to_json())

if __name__ == '__main__':
    dls = dl_server()

    print('## Simulating request')
    dls.simulate_request()

    print('## Waiting for response. Ctrl+C to exit.')
    try: 
        dls.run()
    except KeyboardInterrupt:
        dls.stop()
