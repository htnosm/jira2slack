FROM --platform=linux/amd64 python:3.12-alpine

RUN apk --update --no-cache add \
  curl

ADD requirements.txt /tmp/
RUN pip install -U pip \
  && pip install -U -r /tmp/requirements.txt --no-cache-dir

ENTRYPOINT ["/app/src/docker-entrypoint.sh"]
