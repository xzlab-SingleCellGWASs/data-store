import json
import random

import re
from jsonschema import RefResolver

from dss.util.s3urlcache import S3UrlCache
from tests.json_gen.generator import JsonGenerator

SCHEMA_URL_PATTERN = r'/(?P<version>[0-9]+\.[0-9]+\.[0-9]+)[\w\d/]*/(?P<type>[\w\d]+)(.json)?$'
SCHEMA_URL_REGEX = re.compile(SCHEMA_URL_PATTERN)

class V5JsonGenerator(JsonGenerator):
    def _object(self, schema: dict) -> dict:
        impostor = super(V5JsonGenerator, self)._object(schema)
        described_by = impostor.get('describedBy') if isinstance(impostor, dict) else None
        if described_by is not None:
            schema_url = schema.get('id')
            if schema_url is not None:
                impostor['describedBy'] = schema_url
        return impostor


class V4JsonGenerator(JsonGenerator):
    def _object(self, schema: dict) -> dict:
        impostor = super(V4JsonGenerator, self)._object(schema)
        core = impostor.get('core') if isinstance(impostor, dict) else None
        if core is not None:
            schema_url = schema.get('id')
            if schema_url is not None:
                schema_version, type = SCHEMA_URL_REGEX.search(schema_url).group('version', 'type')
                impostor['core'] = {'schema_url': schema_url, 'type': type, 'schema_version': schema_version}
        return impostor


class HCAJsonGenerator(object):
    """
    Used to generate random JSON from a from a list of URLs containing JSON schemas.
    """
    def __init__(self, schema_urls):
        """
        :param schema_urls: a list of JSON schema URLs.
        """
        self.schemas = dict()
        for url in schema_urls:
            name = url.split('/')[-1]
            self.schemas[name] = {'$ref': url, 'id': url}
        self.cache = S3UrlCache()
        self.resolver = self.resolver_factory()  # The resolver used to dereference JSON '$ref'.
        self._json_gen = {None: JsonGenerator(resolver=self.resolver),
                          4: V4JsonGenerator(resolver=self.resolver),
                          5: V5JsonGenerator(resolver=self.resolver)
                          }

    def generate(self, name: str=None, version: int=None) -> str:
        """
        Chooses a random JSON schema from self.schemas and generates JSON data.
        :param name: the name of a JSON schema to generate. If None, then a random schema is chosen.
        :param version: specify how the generated JSON should describe its self.
        :return: serialized JSON.
        """

        if name is None:
            name = random.choice(list(self.schemas.keys()))
            schema = self.schemas[name]
        else:
            assert name in self.schemas.keys()
            schema = self.schemas[name]
        self.resolve_references(schema)
        generated_json = {name: self._json_gen[version].generate_json(schema)}
        return json.dumps(generated_json)

    def resolve_references(self, schema: dict) -> dict:
        """
        Inlines all `$ref`s in the JSON-schema. The schema is directly modified.
        Example:
            contents of http://test.com/this.json = {'id': 'test file'}

            schema = {'$ref': 'http://test.com/this.json'}
            self.resolve_reference(schema) == {'id': 'test file'}

        :param schema: the JSON schema to use.
        :return: the schema with `$ref`'s inline.
        """
        ref_url = schema.pop('$ref', None)
        if ref_url is not None:
            identifier, ref = self.resolver.resolve(ref_url)
            schema.update(ref)
            schema['id'] = identifier
            self._rec_resolver(schema)

        for value in schema.values():
            if isinstance(value, dict):
                self.resolve_references(value)
            elif isinstance(value, list):
                for i in value:
                    if isinstance(i, dict):
                        self.resolve_references(i)
        return schema

    def _rec_resolver(self, schema: dict) -> None:
        """
        Handles the case where a $ref resolves into another $ref
        """
        ref_url = schema.pop('$ref', None)
        if ref_url is not None:
            identifier, ref = self.resolver.resolve(ref_url)
            schema.update(ref)
            if schema.get('$ref', None):
                self.resolve_references(schema)

    def resolver_factory(self) -> RefResolver:
        """
        Creates a refResolver with a persistent cache
        :return: RefResolver
        """
        def request_json(url):
            return json.loads(self.cache.resolve(url).decode("utf-8"))

        resolver = RefResolver('', '', handlers={'http': request_json, 'https': request_json})
        return resolver
