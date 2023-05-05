#!/bin/sh

interval=${INTERVAL:-300}
prg="./src/main.py"

while true
do
  echo "# $(date +'%Y/%m/%d %H:%M:%S')"
  for config in $(find ./etc/ -name '*.yml' -not -name 'default.yml')
  do
    python ${prg} ${config}
  done
  sleep ${interval}
done
