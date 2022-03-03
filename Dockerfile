FROM python:3

COPY ./ /src

# override this config in Kubernetes with a ConfigMap mounted as a volume to /root/.DANE
RUN mkdir /root/.DANE

# create the mountpoint for storing /input-files and /asr-output dirs
RUN mkdir /mnt/dane-fs

WORKDIR /src

RUN pip install pipenv
RUN pipenv install --system

CMD [ "python", "worker.py" ]