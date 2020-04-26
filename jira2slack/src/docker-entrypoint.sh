#!/bin/sh

interval=${INTERVAL:-300}
check_url=${CHECK_URL:-example.com}
prg="./src/main.py"

while true
do
  echo "# $(date +'%Y/%m/%d %H:%M:%S')"
  if [ "$(curl -s -S -f -m 3 ${check_url} >/dev/null 2>&1 ; echo $?)" -eq 0 ]; then
    for config in $(find ./etc/ -name '*.yml' -not -name 'default.yml')
    do
      python ${prg} ${config}
    done
  else
    echo "skipped"
  fi
  sleep ${interval}
done
