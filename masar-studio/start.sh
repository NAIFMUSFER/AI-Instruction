#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
exec node --env-file-if-exists=.env server/server.mjs
