#!/bin/bash

openssl genrsa 2048 > server.key
chmod 400 server.key
openssl req -new -x509 -nodes -sha256 -days 365 -key server.key -out server.crt

mv server.key securedrop
mv server.crt securedrop