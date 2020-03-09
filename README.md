# Download worker

This is a worker that interacts with [DANE](https://github.com/CLARIAH/DANE) to receive its work. 
It downloads the file provided in the `source_url` of a job.

## Installation

To install the worker run the following:

```
https://github.com/beeldengeluid/download-worker.git
cd download-worker
pip install -r requirements.txt
```

Subsequently, you should be able to start the worker with `python worker.py`, assuming
the [configuration](https://dane.readthedocs.io/en/latest/intro.html#configuration) is correct.

### Configuration

The config file for the worker requires the specification of a whitelist, a list of domains
that the downloader is permitted to download from. Entries in this list should match the format
of the `netloc` attribute returned by [`urlparse`](https://docs.python.org/3/library/urllib.parse.html).
