#!/bin/bash

SOURCE="${BASH_SOURCE[0]}"
DSS_HOME="$(cd -P "$(dirname "$SOURCE")/.." && pwd)"

${DSS_HOME}/scripts/s3rmll.py s3://${DSS_S3_BUCKET}/bundles
${DSS_HOME}/scripts/s3rmll.py s3://${DSS_S3_BUCKET}/files
gsutil -m rm -r gs://${DSS_S3_BUCKET}/bundles/*
gsutil -m rm -r gs://${DSS_S3_BUCKET}/files/*
