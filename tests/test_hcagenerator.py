import json
import os
import sys
import unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from dss import Config, BucketConfig
from tests.json_gen.hca_generator import HCAJsonGenerator
from tests.infra import testmode

v4_schema_urls = [
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/4.6.0/json_schema/analysis_bundle.json",
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/4.6.0/json_schema/assay_bundle.json",
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/4.6.0/json_schema/project_bundle.json",
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/4.6.0/json_schema/sample_bundle.json",
]

v5_schema_urls = [
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/5.0.0/json_schema/bundle/biomaterial.json",
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/5.0.0/json_schema/bundle/protocol.json",
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/5.0.0/json_schema/bundle/project.json",
    "https://raw.githubusercontent.com/HumanCellAtlas/metadata-schema/5.0.0/json_schema/bundle/process.json"
]


@testmode.standalone
class TestHCAGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Config.set_config(BucketConfig.TEST)

    def test_locals(self):
        faker = HCAJsonGenerator(v4_schema_urls)
        for url in v4_schema_urls:
            name = url.split('/')[-1]
            self.assertEqual(faker.schemas[name], {'$ref': url, 'id': url})

    # @unittest.skip("Test is inconsistant")  # TODO (tsmith) remove once tests run consistently
    def test_generation(self):
        faker = HCAJsonGenerator(v4_schema_urls)
        for name in faker.schemas.keys():
            with self.subTest(name):
                fake_json = faker.generate(name)
                fake_json = json.loads(fake_json)
                self.assertIsInstance(fake_json, dict)

    def test_v4generation(self):
        faker = HCAJsonGenerator(v4_schema_urls)
        for name in faker.schemas.keys():
            with self.subTest(name):
                fake_json = faker.generate(name, 4)
                fake_json = json.loads(fake_json)
                self.assertIsInstance(fake_json, dict)
                self.assertEqual(fake_json[name]['core']['schema_url'], faker.schemas[name]['id'])
                self.assertEqual(fake_json[name]['core']['schema_version'], '4.6.0')
                self.assertEqual(fake_json[name]['core']['type'], name.split('.')[0])

    def test_v5generation(self):
        faker = HCAJsonGenerator(v5_schema_urls)
        for name in faker.schemas.keys():
            with self.subTest(name):
                fake_json = faker.generate(name, 5)
                fake_json = json.loads(fake_json)
                self.assertIsInstance(fake_json, dict)
                self.assertEqual(fake_json[name]['describedBy'], faker.schemas[name]['id'])

if __name__ == "__main__":
    unittest.main()
