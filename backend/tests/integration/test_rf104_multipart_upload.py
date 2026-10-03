"""Resumable upload by parts (RF-104): «cortar la red al 50 % y reanudar no reinicia la subida».

The storage is a fake S3 that keeps the parts it received, so the scenario is the real one: open the
upload, send half the parts, lose the network, ask the storage — not the phone's memory — which
parts arrived, sign only the missing ones, and close it. Presigning is real boto3: it signs locally
and needs no network.
"""

# The fake S3 takes boto3's own keyword names (Bucket, Key, UploadId…): that is its whole contract.
# ruff: noqa: N803

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.storage import service as storage
from tests.integration.test_rf076_storage_presign import AUDITOR, TECHNICIAN, client_as
from tests.integration.test_rf076_storage_presign import unit as unit
from tests.integration.test_rf076_storage_presign import units as units

pytestmark = pytest.mark.integration

MB = 1024 * 1024


class FakeS3:
    """Just enough of S3's multipart API to tell a resumed upload from a restarted one."""

    def __init__(self) -> None:
        self.uploads: dict[str, dict[str, Any]] = {}
        self.completed: dict[str, list[dict[str, Any]]] = {}
        self.page_size = 1000

    def create_multipart_upload(self, *, Bucket: str, Key: str, ContentType: str) -> dict[str, Any]:
        upload_id = f"up-{len(self.uploads) + 1}"
        self.uploads[upload_id] = {"key": Key, "parts": {}}
        return {"UploadId": upload_id}

    def receive(self, upload_id: str, number: int, size: int) -> None:
        """What the phone's PUT to a presigned part URL does."""
        self.uploads[upload_id]["parts"][number] = {"etag": f'"etag-{number}"', "size": size}

    def list_parts(
        self, *, Bucket: str, Key: str, UploadId: str, PartNumberMarker: int = 0
    ) -> dict[str, Any]:
        if UploadId not in self.uploads:
            raise RuntimeError("NoSuchUpload")
        numbers = sorted(n for n in self.uploads[UploadId]["parts"] if n > PartNumberMarker)
        page, rest = numbers[: self.page_size], numbers[self.page_size :]
        result: dict[str, Any] = {
            "Parts": [
                {
                    "PartNumber": n,
                    "ETag": self.uploads[UploadId]["parts"][n]["etag"],
                    "Size": self.uploads[UploadId]["parts"][n]["size"],
                }
                for n in page
            ],
            "IsTruncated": bool(rest),
        }
        if rest:
            result["NextPartNumberMarker"] = page[-1]
        return result

    def complete_multipart_upload(
        self, *, Bucket: str, Key: str, UploadId: str, MultipartUpload: dict[str, Any]
    ) -> None:
        expected = self.uploads[UploadId]["parts"]
        for part in MultipartUpload["Parts"]:
            if expected.get(part["PartNumber"], {}).get("etag") != part["ETag"]:
                raise RuntimeError("InvalidPart")
        self.completed[Key] = MultipartUpload["Parts"]
        del self.uploads[UploadId]

    def abort_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str) -> None:
        self.uploads.pop(UploadId, None)


@pytest.fixture
def s3(monkeypatch: pytest.MonkeyPatch) -> FakeS3:
    fake = FakeS3()
    monkeypatch.setattr(storage, "_internal_client", lambda: fake)
    return fake


def open_upload(api: TestClient, size: int = 12 * MB) -> dict[str, Any]:
    response = api.post(
        "/api/v1/storage/units/GYE/multipart",
        json={
            "purpose": "evidencia",
            "kind": "audio",
            "filename": "nota de campo.wav",
            "content_type": "audio/wav",
            "size_bytes": size,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestRf104:
    def test_rf_104_cutting_at_half_and_resuming_does_not_start_over(
        self, session: Session, unit, s3: FakeS3
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            upload = open_upload(api, size=4 * storage.PART_SIZE)
            assert upload["part_count"] == 4
            assert upload["storage_key"].startswith("GYE/evidencia/audio/")
            ref = {"storage_key": upload["storage_key"], "upload_id": upload["upload_id"]}

            urls = api.post(
                "/api/v1/storage/units/GYE/multipart/parts",
                json={**ref, "part_numbers": [1, 2, 3, 4]},
            ).json()["urls"]
            assert sorted(urls) == ["1", "2", "3", "4"]
            assert "partNumber=1" in urls["1"] and "uploadId=" in urls["1"]

            # Half arrives; then the network goes.
            s3.receive(upload["upload_id"], 1, storage.PART_SIZE)
            s3.receive(upload["upload_id"], 2, storage.PART_SIZE)

            # Back online: the storage, not the phone, says what arrived.
            arrived = api.post("/api/v1/storage/units/GYE/multipart/status", json=ref).json()[
                "parts"
            ]
            assert [part["part_number"] for part in arrived] == [1, 2]

            missing = [n for n in range(1, 5) if n not in {p["part_number"] for p in arrived}]
            resumed = api.post(
                "/api/v1/storage/units/GYE/multipart/parts", json={**ref, "part_numbers": missing}
            ).json()["urls"]
            assert sorted(resumed) == ["3", "4"]
            s3.receive(upload["upload_id"], 3, storage.PART_SIZE)
            s3.receive(upload["upload_id"], 4, storage.PART_SIZE)

            done = api.post(
                "/api/v1/storage/units/GYE/multipart/complete",
                json={
                    **ref,
                    "parts": [{"part_number": n, "etag": f'"etag-{n}"'} for n in (4, 3, 2, 1)],
                },
            )
        assert done.status_code == 200, done.text
        assert [part["PartNumber"] for part in s3.completed[upload["storage_key"]]] == [1, 2, 3, 4]

    def test_the_same_limits_as_a_whole_upload(self, session: Session, unit, s3: FakeS3) -> None:
        with client_as(session, TECHNICIAN) as api:
            too_big = api.post(
                "/api/v1/storage/units/GYE/multipart",
                json={
                    "purpose": "evidencia",
                    "kind": "audio",
                    "filename": "x.wav",
                    "content_type": "audio/wav",
                    "size_bytes": 21 * MB,
                },
            )
            wrong_type = api.post(
                "/api/v1/storage/units/GYE/multipart",
                json={
                    "purpose": "evidencia",
                    "kind": "audio",
                    "filename": "x.exe",
                    "content_type": "application/x-msdownload",
                    "size_bytes": MB,
                },
            )
        assert too_big.status_code == 422
        assert wrong_type.status_code == 422
        assert s3.uploads == {}

    def test_a_key_of_another_unit_does_not_exist_here(
        self, session: Session, unit, s3: FakeS3
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            for path, extra in (
                ("parts", {"part_numbers": [1]}),
                ("status", {}),
                ("complete", {"parts": [{"part_number": 1, "etag": "x"}]}),
                ("abort", {}),
            ):
                response = api.post(
                    f"/api/v1/storage/units/GYE/multipart/{path}",
                    json={"storage_key": "MAN/evidencia/audio/x.wav", "upload_id": "up-1", **extra},
                )
                assert response.status_code == 404, path

    def test_part_numbers_out_of_range_are_refused(
        self, session: Session, unit, s3: FakeS3
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            upload = open_upload(api)
            response = api.post(
                "/api/v1/storage/units/GYE/multipart/parts",
                json={
                    "storage_key": upload["storage_key"],
                    "upload_id": upload["upload_id"],
                    "part_numbers": [0, 1],
                },
            )
        assert response.status_code == 422

    def test_duplicated_or_unknown_parts_do_not_close(
        self, session: Session, unit, s3: FakeS3
    ) -> None:
        with client_as(session, TECHNICIAN) as api:
            upload = open_upload(api)
            ref = {"storage_key": upload["storage_key"], "upload_id": upload["upload_id"]}
            s3.receive(upload["upload_id"], 1, storage.PART_SIZE)
            duplicated = api.post(
                "/api/v1/storage/units/GYE/multipart/complete",
                json={**ref, "parts": [{"part_number": 1, "etag": '"etag-1"'}] * 2},
            )
            unknown = api.post(
                "/api/v1/storage/units/GYE/multipart/complete",
                json={**ref, "parts": [{"part_number": 1, "etag": '"otra"'}]},
            )
        assert duplicated.status_code == 422
        assert unknown.status_code == 422
        assert s3.completed == {}

    def test_status_of_a_closed_upload_is_404(self, session: Session, unit, s3: FakeS3) -> None:
        with client_as(session, TECHNICIAN) as api:
            upload = open_upload(api)
            ref = {"storage_key": upload["storage_key"], "upload_id": upload["upload_id"]}
            api.post("/api/v1/storage/units/GYE/multipart/abort", json=ref)
            assert (
                api.post("/api/v1/storage/units/GYE/multipart/status", json=ref).status_code == 404
            )

    def test_the_listing_follows_pagination(self, s3: FakeS3) -> None:
        s3.page_size = 2
        s3.uploads["up-9"] = {"key": "GYE/k", "parts": {}}
        for n in range(1, 6):
            s3.receive("up-9", n, 10)
        assert [p["part_number"] for p in storage.uploaded_parts("GYE/k", "up-9")] == [
            1,
            2,
            3,
            4,
            5,
        ]

    def test_who_cannot_upload_cannot_open_one(self, session: Session, unit, s3: FakeS3) -> None:
        with client_as(session, AUDITOR) as api:
            response = api.post(
                "/api/v1/storage/units/GYE/multipart",
                json={
                    "purpose": "evidencia",
                    "kind": "audio",
                    "filename": "x.wav",
                    "content_type": "audio/wav",
                    "size_bytes": MB,
                },
            )
        assert response.status_code == 403

    def test_part_count_rounds_up(self) -> None:
        assert storage.part_count(1) == 1
        assert storage.part_count(storage.PART_SIZE) == 1
        assert storage.part_count(storage.PART_SIZE + 1) == 2
