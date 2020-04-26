FROM python:3.8-alpine

RUN apk --update --no-cache add \
  curl

ADD requirements.txt /tmp/
RUN pip install -U -r /tmp/requirements.txt --no-cache-dir

ENTRYPOINT ["/app/src/docker-entrypoint.sh"]
