# Download worker

This is a worker that interacts with [DANE](https://github.com/CLARIAH/DANE) to receive its work.
It downloads the file provided in the `target.url` of a DANE document.

Running DANE and any DANE worker is most manageable using Kubernetes, instructions for setting up a DANE Kubernetes cluster will be provided in a separate (Helm) repository.

## Local installation (for development)

Make sure to install [pipenv](https://github.com/pypa/pipenv)

Then to install the worker run the following:

```bash
git clone https://github.com/beeldengeluid/download-worker.git
cd download-worker
pipenv install
```

### Configuration

Make sure to copy `config_k8s.yml` to `config.yml` in the main directory of this repo. Study the inline comments to properly configure this DANE worker. Most importantly a valid RabbitMQ server and Elasticsearch cluster is required to get this DANE worker to start-up.


### Run

After installing and configuring the DANE worker should start with:

```bash
python worker.py
```
