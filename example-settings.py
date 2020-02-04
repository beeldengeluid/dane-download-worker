config = {
	#message queue parameters
        'RABBITMQ': {
            'host': 'localhost',
            'port': '5672', 
            'exchange': 'DANE-exchange',
            'response_queue': 'DANE-response-queue',
            'user': 'DANE',
            'password': 'DANE_PW'
        },
        # Domains we are permitted to download from
        'WHITELIST': [
           'some-domain.example'
        ],
        # URL to send DANE api requests
        'API': 'http://localhost:5500/DANE/',
        # Under this threshold downloading is postponed until more free space
        # becomes available. Counts free space on entire partition.
        'FS_THRESHOLD': '10GB'
}
