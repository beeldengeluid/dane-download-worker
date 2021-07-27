FROM python:3

COPY ./ /src
COPY Pipfile Pipfile.lock /src/

# override this config in Kubernetes with a ConfigMap mounted as a volume to /root/.DANE
RUN mkdir /root/.DANE
COPY config.yml /root/.DANE

# create the mountpoint for storing /input-files and /asr-output dirs
RUN mkdir /mnt/dane-fs

WORKDIR /src

RUN pip install pipenv
RUN pipenv install --system

CMD [ "python", "worker.py" ]