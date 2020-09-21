#!/usr/bin/env bash

facets=('server' 'client')

for i in "${!facets[@]}";
do
  key_filename="${facets[$i]}.key"
  cert_filename="${facets[$i]}.crt"

  echo "${key_filename}"
  echo "${cert_filename}"
  openssl genrsa 2048 > "${key_filename}"
  chmod 400 "${key_filename}"
  openssl req -new -x509 -nodes -sha256 -days 365 -key "${key_filename}" -out "${cert_filename}"

  mv "${key_filename}" securedrop/tests
  mv "${cert_filename}" securedrop/tests
done