FROM docker.io/python:3.11

COPY ./ /src

# override this config in Kubernetes with a ConfigMap mounted as a volume to /root/.DANE
RUN mkdir /root/.DANE

# create the mountpoint for storing /input-files and /asr-output dirs
RUN mkdir /mnt/dane-fs

WORKDIR /src

RUN pip install poetry
RUN poetry config virtualenvs.create false && poetry install --no-dev --no-interaction --no-ansi

CMD [ "python", "worker.py" ]
