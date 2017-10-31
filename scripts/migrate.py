#!/usr/bin/env python

import os
import string
import argparse
from threading import Lock

from urllib3.util import parse_url
from concurrent.futures import ThreadPoolExecutor

import google.cloud.storage
from cloud_blobstore.s3 import S3BlobStore
from cloud_blobstore.gs import GSBlobStore
from cloud_blobstore import BlobNotFoundError
from size_metadata_migration_kernel import MigrationKernel


count = 0
mutex = Lock()


class AdminGSBlobstore(GSBlobStore):
    def __init__(self):
        super(GSBlobStore, self).__init__()
        self.gcp_client = google.cloud.storage.Client()
        self.bucket_map = dict()  # type: typing.MutableMapping[str, Bucket]


def increment_count():
    global count
    mutex.acquire()
    try:
        count += 1
    finally:
        mutex.release()


def parse_args():
    parser = argparse.ArgumentParser(description="Migrates S3 files in parallel")
    parser.add_argument('url',
                        help="URL of bucket that you wish to migrate, e.g. s3://bucket/files or gs://bucket/bundles")
    args = parser.parse_args()
    return parse_url(args.url)


def migrate_object(replica, handle, bucket, key):
    try:
        MigrationKernel(handle, bucket, key).migrate()
        increment_count()
        print(f"{count} {replica}://{bucket}/{key}")
    except BlobNotFoundError:
        increment_count()
        print(f"{count} ERROR: Unabel to migrate {replica}://{bucket}/{key} Blob not found")


def migrate_objs_with_prefix(replica, handle, bucket, prefix):
    for key in handle.list(bucket, prefix):
        migrate_object(replica, handle, bucket, key)


def concurrent_migration(handle, url):
    alphanumeric = string.ascii_lowercase + '0987654321'
    prefixes = [f'{a}{b}' for a in alphanumeric for b in alphanumeric]

    with ThreadPoolExecutor(max_workers=48) as executor:
        for pfx in prefixes:
            executor.submit(migrate_objs_with_prefix,
                            url.scheme,
                            handle,
                            url.host,
                            f"{url.path}/{pfx}".lstrip("/"))


url = parse_args()
if "s3" == url.scheme:
    concurrent_migration(S3BlobStore(), url)
elif "gs" == url.scheme:
    concurrent_migration(AdminGSBlobstore(), url)
else:
    f"Scheme not recognized for {url}"
