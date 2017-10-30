#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
DSS_HOME="$(cd -P "$(dirname "$SOURCE")/.." && pwd)"

echo "Migrating s3 replica"
${DSS_HOME}/scripts/migrate.py s3://${DSS_S3_BUCKET}/files
${DSS_HOME}/scripts/migrate.py s3://${DSS_S3_BUCKET}/bundles

echo "Migrating gs replica"
${DSS_HOME}/scripts/migrate.py gs://${DSS_GS_BUCKET}/files --gcs-credentials="${GOOGLE_APPLICATION_CREDENTIALS}"
${DSS_HOME}/scripts/migrate.py gs://${DSS_GS_BUCKET}/bundles --gcs-credentials="${GOOGLE_APPLICATION_CREDENTIALS}"
