#!/usr/bin/env python

import os
import argparse
from threading import Lock

from urllib3.util import parse_url
from concurrent.futures import ThreadPoolExecutor

from cloud_blobstore.s3 import S3BlobStore
from cloud_blobstore.gs import GSBlobStore
from cloud_blobstore import BlobNotFoundError
from migration_kernel import MigrationKernel


count = 0
mutex = Lock()


def increment_count():
    global count
    mutex.acquire()
    try:
        count += 1
    finally:
        mutex.release()


def parse_args():
    parser = argparse.ArgumentParser(description="Migrates S3 files in parallel")
    parser.add_argument('url', help="URL of bucket that you wish to migrate, e.g. s3://bucket/files or gs://bucket/bundles")
    parser.add_argument('--gcs-credentials',
                        dest="gcs_credentials",
                        default="",
                        help="path to google applications credentials json file")
    args = parser.parse_args()
    return parse_url(args.url), args.gcs_credentials


def migrate_object(handle, bucket, key):
    try:
        MigrationKernel(handle, bucket, key).migrate()
        increment_count()
        print(count, key)
    except BlobNotFoundError:
        increment_count()
        print(f"{count} Unabel to migrate {bucket}/{key} Blob not found")


def migrate_objects(handle, url):
    with ThreadPoolExecutor(max_workers=50) as executor:
        for key in handle.list(url.host, url.path.lstrip('/')):
            executor.submit(migrate_object, handle, url.host, key)


url, gs_creds = parse_args()
if "s3" == url.scheme:
    migrate_objects(S3BlobStore(), url)
elif "gs" == url.scheme:
    migrate_objects(GSBlobStore(gs_creds), url)
else:
    f"Scheme not recognized for {url}"
