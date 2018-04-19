import json
import logging
from collections import deque
from typing import Mapping, Optional, Set

import time
from cloud_blobstore import BlobNotFoundError, BlobStoreError

from dss import Config, Replica
from dss.storage.hcablobstore import BundleFileMetadata, BundleMetadata
from dss.storage.identifiers import BundleFQID, ObjectIdentifier, TombstoneID
from dss.util import create_blob_key
from dss.util.types import JSON

logger = logging.getLogger(__name__)


class Bundle:
    """
    In the context of indexing, a bundle is a collection of metadata files stored in a given replica. It is uniquely
    identified by an FQID. One of the metadata files, the bundle manifest, is a description of the remaining files.
    Note that indexeing is agnostic to the concept of bundles having multiple versions: instances of this class
    always represent a siongle bundle version and each version of a conceptual bundle is represented by a separate
    instance of this class.
    """

    def __init__(self, replica: Replica, fqid: BundleFQID, manifest: JSON, files: Mapping[str, JSON]) -> None:
        self.replica = replica
        self.fqid = fqid
        self.manifest = manifest
        self.files = files

    @classmethod
    def load(cls, indexer, fqid: BundleFQID):
        manifest = cls._read_bundle_manifest(indexer.replica, fqid)
        files = cls._read_file_infos(indexer, fqid, manifest)
        self = cls(indexer.replica, fqid, manifest=manifest, files=files)
        return self

    @classmethod
    def _read_bundle_manifest(cls, replica: Replica, fqid: BundleFQID) -> dict:
        handle = Config.get_blobstore_handle(replica)
        bucket_name = replica.bucket
        manifest_string = handle.get(bucket_name, fqid.to_key()).decode("utf-8")
        logger.debug("Read bundle manifest from bucket %s with bundle key %s: %s",
                     bucket_name, fqid.to_key(), manifest_string)
        manifest = json.loads(manifest_string, encoding="utf-8")
        return manifest

    @classmethod
    def _read_file_infos(cls, indexer, fqid: BundleFQID, manifest: JSON) -> Mapping[str, JSON]:
        replica = indexer.replica
        handle = Config.get_blobstore_handle(replica)
        bucket_name = replica.bucket
        files_info_original = manifest[BundleMetadata.FILES]
        assert isinstance(files_info_original, list)
        files_info = deque((file, 0) for file in files_info_original if file[BundleFileMetadata.INDEXED] is True)
        wait_time = 5
        load_time = 5
        index_files = {}
        while files_info:
            file_info, attempts = files_info.popleft()
            content_type = file_info[BundleFileMetadata.CONTENT_TYPE]
            file_name = file_info[BundleFileMetadata.NAME]
            if content_type.startswith('application/json'):
                file_blob_key = create_blob_key(file_info)
                try:
                    file_string = handle.get(bucket_name, file_blob_key).decode("utf-8")
                except BlobStoreError as ex:
                    # Requeue at the end, yielding to other files we may not have tried yet
                    files_info.append((file_info, attempts + 1))
                    if wait_time + len(files_info) * load_time < indexer.remaining_time:
                        logger.warning(f"In bundle {fqid} the file '{file_name}' is marked for indexing yet could "
                                       f"not be accessed. Retrying.")
                        # Only wait before retries, not first attempts to load a file.
                        if attempts:
                            time.sleep(wait_time)
                    else:
                        raise RuntimeError(f"{ex} This bundle will not be indexed. Bundle: {fqid}, File Blob Key: "
                                           f"{file_blob_key}, File Name: '{file_name}'") from ex
                else:
                    try:
                        file_json = json.loads(file_string)
                        # TODO (mbaumann) Are there other JSON-related exceptions that should be checked below?
                    except json.decoder.JSONDecodeError as ex:
                        logger.warning(f"In bundle {fqid} the file '{file_name}' is marked for indexing yet could "
                                       f"not be parsed. This file will not be indexed. Exception: {ex}")
                    else:
                        logger.debug(f"Loaded file: {file_name}")
                        index_files[file_name] = file_json
            else:
                logger.warning(f"In bundle {fqid} the file '{file_name}' is marked for indexing yet has "
                               f"content type '{content_type}' instead of the required content type "
                               f"'application/json'. This file will not be indexed.")
        return index_files

    def lookup_tombstone(self) -> Optional['Tombstone']:
        """
        Return the tombstone placed on this bundle in storage or None if none exists.
        """
        for all_versions in (False, True):
            tombstone_id = self.fqid.to_tombstone_id(all_versions=all_versions)
            try:
                return Tombstone.load(self.replica, tombstone_id)
            except BlobNotFoundError:
                pass
        return None

    def __str__(self):
        return f"{self.__class__.__name__}(replica={self.replica}, fqid='{self.fqid}')"


class Tombstone:
    """
    A tombstone is a storage object whose FQID matches that of a given single bundle or all bundles for a given UUID.
    Bundles for which there is a tombstone must be omitted from the index.
    """
    def __init__(self, replica: Replica, fqid: TombstoneID, body: JSON) -> None:
        self.replica = replica
        self.fqid = fqid
        self.body = body

    @classmethod
    def load(cls, replica: Replica, tombstone_id: TombstoneID):
        blobstore = Config.get_blobstore_handle(replica)
        bucket_name = replica.bucket
        body = json.loads(blobstore.get(bucket_name, tombstone_id.to_key()))
        self = cls(replica, tombstone_id, body)
        return self

    def list_dead_bundles(self) -> Set[BundleFQID]:
        blobstore = Config.get_blobstore_handle(self.replica)
        bucket_name = self.replica.bucket
        assert isinstance(self.fqid, TombstoneID)
        if self.fqid.is_fully_qualified():
            # If a version is specified, return just that bundle …
            return {self.fqid.to_bundle_fqid()}
        else:
            # … otherwise, return all bundles with the same UUID from the index.
            prefix = self.fqid.to_key_prefix()
            fqids = map(ObjectIdentifier.from_key, blobstore.list(bucket_name, prefix))
            return set(fqid for fqid in fqids if type(fqid) == BundleFQID)

    def __str__(self):
        return f"{self.__class__.__name__}(replica={self.replica}, fqid='{self.fqid}')"
