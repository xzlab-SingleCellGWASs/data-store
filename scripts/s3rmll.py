#!/usr/bin/env python

import argparse
from threading import Lock

from urllib3.util import parse_url
import boto3
from concurrent.futures import ThreadPoolExecutor

s3 = boto3.client('s3')
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
    parser = argparse.ArgumentParser(description="Delete S3 files in parallel")
    parser.add_argument('s3url', help="S3 URL of bucket (and optionally path) that you wish to delete")
    args = parser.parse_args()
    return parse_url(args.s3url)


def delete_object_from_s3(bucket, key):
    boto3.resource('s3').Bucket(bucket).Object(key).delete()
    increment_count()
    print(count, key)


def delete_object_under(s3url):
    with ThreadPoolExecutor(max_workers=50) as executor:
        paginator = s3.get_paginator('list_objects')
        for page in paginator.paginate(Bucket=s3url.host, Prefix=s3url.path.lstrip('/')):
            if 'Contents' in page:
                for o in page['Contents']:
                    executor.submit(delete_object_from_s3, s3url.host, o['Key'])


s3url = parse_args()
delete_object_under(s3url)
