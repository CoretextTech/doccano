#!/bin/bash

if [[ ! -v ${DATA_URL} ]]; then
    echo "DATA_URL is unset, running empty .."
elif [[ -z "DATA_URL" ]]; then
    echo "DATA_URL is set to an empty string, running empty .."
else
    aws s3 cp "${DATA_URL}" "/doccano/db.sqlite"
fi

exec "$@"
