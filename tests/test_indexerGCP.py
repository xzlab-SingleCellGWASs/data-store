#!/usr/bin/env python
# coding: utf-8

import json
import logging
import os
import sys
import threading
import unittest
from http.server import HTTPServer
from typing import Dict

from tests.indexer_test_base import TestIndexerBase, findOpenPort, PostTestHandler, HTTPInfo

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from dss.config import IndexSuffix
from dss.events.handlers.index import process_new_gs_indexable_object
from dss.util.es import ElasticsearchServer
from tests.infra import start_verbose_logging

# The moto mock has two defects that show up when used by the dss core storage system.
# Use actual S3 until these defects are fixed in moto.
# TODO (mbaumann) When the defects in moto have been fixed, remove True from the line below.
USE_AWS_S3 = bool(os.environ.get("USE_AWS_S3", True))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


start_verbose_logging()


#
# Basic test for DSS indexer:
#   1. Populate S3 bucket with data for a bundle as defined
#      in the HCA Storage System Disk Format specification
#   2. Inject a mock S3 event into function used by the indexing AWS Lambda
#   3. Read and process the bundle manifest to produce an index as
#      defined in HCA Storage System Index, Query, and Eventing Functional Spec & Use Cases
#      The index document is then added to Elasticsearch
#   4. Perform a search to verify the bundle index document is in Elasticsearch.
#   5. Verify the structure and content of the index document
#

class ESInfo:
    server = None

def setUpModule():
    IndexSuffix.name = __name__.rsplit('.', 1)[-1]
    HTTPInfo.port = findOpenPort()
    HTTPInfo.server = HTTPServer((HTTPInfo.address, HTTPInfo.port), PostTestHandler)
    HTTPInfo.thread = threading.Thread(target=HTTPInfo.server.serve_forever)
    HTTPInfo.thread.start()

    ESInfo.server = ElasticsearchServer()
    os.environ['DSS_ES_PORT'] = str(ESInfo.server.port)

def tearDownModule():
    ESInfo.server.shutdown()
    HTTPInfo.server.shutdown()
    IndexSuffix.reset()
    os.unsetenv('DSS_ES_PORT')

class TestGCPIndexer(TestIndexerBase, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().indexer_setup("gcp")

    def process_new_indexable_object(self, event, logger):
        process_new_gs_indexable_object(event, logger)

    def create_bundle_created_event(self, bundle_key, bucket_name) -> Dict:
        with open(os.path.join(os.path.dirname(__file__), "sample_gs_bundle_created_event.json")) as fh:
            sample_event = json.load(fh)
        sample_event["bucket"] = bucket_name
        sample_event["name"] = bundle_key
        return sample_event

if __name__ == "__main__":
    unittest.main()
