#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  CREATE DATABASE project1;
  CREATE DATABASE project2;
  CREATE DATABASE project3;
  
  GRANT ALL PRIVILEGES ON DATABASE project1 TO postgres;
  GRANT ALL PRIVILEGES ON DATABASE project2 TO postgres;
  GRANT ALL PRIVILEGES ON DATABASE project3 TO postgres;
EOSQL 