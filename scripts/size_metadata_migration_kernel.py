import os
import io
import sys
import json

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from dss.hcablobstore import FileMetadata, HCABlobStore, BundleMetadata, BundleFileMetadata


class MigrationKernel:
    def __init__(self, handle, bucket, key):
        self.handle = handle
        self.bucket = bucket
        self.key = key


    def migrate_file_manifest(self):
        manifest = json.loads(self.handle.get(self.bucket, self.key).decode("utf-8"))

        blobpath = ("blobs/" + ".".join((
            manifest[FileMetadata.SHA256],
            manifest[FileMetadata.SHA1],
            manifest[FileMetadata.S3_ETAG],
            manifest[FileMetadata.CRC32C])))

        manifest[FileMetadata.SIZE] = self.handle.get_size(self.bucket, blobpath)

        manifest = json.dumps(manifest)
        self.handle.upload_file_handle(self.bucket,
                                       self.key,
                                       io.BytesIO(manifest.encode("utf-8")))


    def migrate_bundle_manifest(self):
        manifest = json.loads(self.handle.get(self.bucket, self.key).decode("utf-8"))
        for file in manifest[BundleMetadata.FILES]:
            filekey = "files/{}.{}".format(file[BundleFileMetadata.UUID], file[BundleFileMetadata.VERSION])
            file_manifest = json.loads(self.handle.get(self.bucket, filekey).decode("utf-8"))
            file['size'] = file_manifest[FileMetadata.SIZE]

        manifest = json.dumps(manifest)
        self.handle.upload_file_handle(self.bucket,
                                       self.key,
                                       io.BytesIO(manifest.encode("utf-8")))


    def migrate(self):
        if self.key.startswith("files"):
            self.migrate_file_manifest()
        elif self.key.startswith("bundles"):
            self.migrate_bundle_manifest()
        else:
            raise Exception(f"Attempted to migrate unknown object {self.bucket}/{self.key}")
