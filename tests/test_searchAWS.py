#!/usr/bin/env python
# coding: utf-8

import logging
import os
import sys

import unittest

from tests.search_test_base import TestSearchBase

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

import dss
from dss.config import IndexSuffix
from dss.util.es import ElasticsearchServer
from tests.infra import start_verbose_logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

start_verbose_logging()


# class ESInfo:
#     server = None

def setUpModule():
    IndexSuffix.set_name(__name__.rsplit('.', 1)[-1])
    # ESInfo.server = ElasticsearchServer()
    # os.environ['DSS_ES_PORT'] = str(ESInfo.server.port)
    os.environ['DSS_ES_PORT'] = '9200'

def tearDownModule():
    # ESInfo.server.shutdown()
    IndexSuffix.reset()
    os.unsetenv('DSS_ES_PORT')


class TestAWSSearch(TestSearchBase, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().search_setup(dss.Replica.aws)


if __name__ == "__main__":
    unittest.main()
