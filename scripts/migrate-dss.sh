#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
DSS_HOME="$(cd -P "$(dirname "$SOURCE")/.." && pwd)"

${DSS_HOME}/scripts/migrate.py s3://${DSS_S3_BUCKET}/files
${DSS_HOME}/scripts/migrate.py s3://${DSS_S3_BUCKET}/bundles
${DSS_HOME}/scripts/migrate.py gs://${DSS_GS_BUCKET}/files
${DSS_HOME}/scripts/migrate.py gs://${DSS_GS_BUCKET}/bundles
