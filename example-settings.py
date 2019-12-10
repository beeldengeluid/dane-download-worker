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

        'WHITELIST': [
           'some-domain.example'
        ]
}
