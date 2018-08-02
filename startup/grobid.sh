#!/bin/bash

docker pull lfoppiano/grobid:0.5.1

docker run -t --rm --init -p 8080:8070 -p 8081:8071 lfoppiano/grobid:0.5.1 &

start=$(curl localhost:8071/api/isalive)

if [ $start = "true" ]
then
    echo "Grobid is Running."
fi

