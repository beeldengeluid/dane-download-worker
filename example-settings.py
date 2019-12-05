config = {
	#webserver parameters
	'API_HOST' : '0.0.0.0',
	'API_PORT' : 5500,
	
	'ES_HOST': 'deves2001.beeldengeluid.nl',
	'ES_PORT': 9200,

	#message queue parameters
        'RABBITMQ': {
            'host': 'localhost',
            'port': '5672', 
            'exchange': 'DANE-exchange',
            'response_queue': 'DANE-response-queue'
        },

        'MARIADB': {
            'user': 'root',
            'password': 'pw',
            'host': 'localhost',
            'port': '3306',
            'database': 'DANE-sql-store'
            },

	"IN_FOLDER": "/home/nvnoord/container-data/IN/{id}/",
	"OUT_FOLDER": "/home/nvnoord/container-data/OUT/{id}/",
}
