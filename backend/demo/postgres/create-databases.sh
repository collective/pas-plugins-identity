#!/bin/bash
# Create the databases the demo stack needs beyond the one Postgres makes.
#
# The official image creates exactly one database, named by POSTGRES_DB, and
# then runs everything in /docker-entrypoint-initdb.d once. That is the only
# hook there is for a second one, so this is a script rather than a setting.
#
# Three databases in one server:
#
#   idp     the ZODB of id.localhost, through RelStorage
#   rp      the ZODB of plone.localhost, through RelStorage
#   audit   the identity provider's authentication records
#
# Separate databases rather than separate schemas in one. RelStorage creates
# its own tables on first start and has no notion of sharing a database with
# another storage, so two sites in one database would be two sites in one
# ZODB. Separating by schema would work and would mean setting a search_path
# everywhere, for no benefit here: a database is free and unambiguous.
#
# Only ever runs on an empty data directory. Adding a database later means
# creating it by hand, or removing the volume:
#
#   docker compose -f docker-compose.demo.yml down --volumes
set -euo pipefail

# ``CREATE DATABASE`` cannot run inside a transaction block, so psql is left
# to its default of one implicit transaction per statement rather than being
# given --single-transaction.
psql --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
     --set ON_ERROR_STOP=1 <<-SQL
	CREATE DATABASE idp OWNER ${POSTGRES_USER};
	CREATE DATABASE rp OWNER ${POSTGRES_USER};
SQL

echo "Created the idp and rp databases; ${POSTGRES_DB} is the audit one."
