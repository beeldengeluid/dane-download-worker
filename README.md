[![Test, lint and build main branch](https://github.com/beeldengeluid/dane-download-worker/actions/workflows/main-branch.yml/badge.svg)](https://github.com/beeldengeluid/dane-download-worker/actions/workflows/main-branch.yml)  
# Download worker

This is a worker that interacts with [DANE](https://github.com/CLARIAH/DANE) to receive its work.
It downloads the file provided in the `target.url` of a DANE document.

Running DANE and any DANE worker is most convenient using Kubernetes, instructions for setting up DANE in a Kubernetes cluster will be provided in a separate repository.

## Local installation (for development)

Make sure to install [poetry](https://github.com/python-poetry/poetry)

Then to install the worker run the following:

```bash
git clone https://github.com/beeldengeluid/download-worker.git
cd dane-download-worker
poetry install
```

### Configuration

Make sure to copy `config_k8s.yml` to `config.yml` in the main directory of this repo. Study the inline comments to properly configure this DANE worker. Most importantly a valid [RabbitMQ](https://www.rabbitmq.com/) server and [Elasticsearch](https://www.elastic.co/elasticsearch/) cluster is required to get this DANE worker to start-up.


### Run

After (local) installation & configuration, make sure to activate the Python virtual environment via:

```bash
poetry shell
```

Then to run the worker:

```bash
python worker.py
```

### Run local unit tests

Check if your local deployment is ok by running:

```bash
./scripts/check-project.sh
```

## Building the image

From the main directory, run:

```bash
docker build -t dane-download-worker .
```
