import pytest
from moto import mock_aws

from app.services.storage import LocalFileStorage, S3FileStorage


def test_local_storage_upload_and_get_url(tmp_path):
    store = LocalFileStorage(base_dir=str(tmp_path), base_url="http://localhost:8000")

    url = store.upload_file("reports/sample.csv", b"a,b\n1,2\n")

    assert url == "http://localhost:8000/static/uploads/reports/sample.csv"
    assert (tmp_path / "reports" / "sample.csv").read_bytes() == b"a,b\n1,2\n"
    assert store.get_file_url("reports/sample.csv") == url


@pytest.mark.parametrize("bad_key", ["../escape.csv", "/etc/passwd", "a/../../b.csv"])
def test_local_storage_rejects_path_traversal(tmp_path, bad_key):
    store = LocalFileStorage(base_dir=str(tmp_path), base_url="http://localhost:8000")

    with pytest.raises(ValueError):
        store.upload_file(bad_key, b"malicious")


@mock_aws
def test_s3_storage_upload_and_get_url():
    store = S3FileStorage(
        bucket="test-bucket",
        region="us-east-1",
        endpoint_url=None,
        access_key="testing",
        secret_key="testing",
        expiry_seconds=3600,
    )

    url = store.upload_file("docs/sample.csv", b"hello,world\n1,2\n")

    assert "test-bucket" in url
    assert "docs" in url and "sample.csv" in url

    obj = store.client.get_object(Bucket="test-bucket", Key="docs/sample.csv")
    assert obj["Body"].read() == b"hello,world\n1,2\n"

    # get_file_url works for a key that's already stored, without re-uploading
    url2 = store.get_file_url("docs/sample.csv")
    assert url2.startswith("http")
