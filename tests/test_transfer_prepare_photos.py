import pytest

from src.transfer.photos import (
    PreparePhotoError,
    image_suffix,
    photo_ids_to_link,
    prepare_photo_path,
)


def test_image_suffix_accepts_jpeg_png_webp():
    assert image_suffix(b"\xff\xd8\xff" + b"x" * 20) == ".jpg"
    assert image_suffix(b"\x89PNG\r\n\x1a\n" + b"x" * 20) == ".png"
    assert image_suffix(b"RIFF" + b"xxxx" + b"WEBP" + b"x" * 8) == ".webp"


def test_image_suffix_rejects_other_bytes_and_oversized():
    with pytest.raises(PreparePhotoError):
        image_suffix(b"not-an-image-file!!")
    with pytest.raises(PreparePhotoError):
        image_suffix(b"\xff\xd8\xff" + b"x" * (8 * 1024 * 1024))


def test_photo_ids_to_link_keeps_only_this_requests_unlinked_photos():
    rows = [
        {"photo_id": "a", "transfer_id": "t1", "shipment_id": None},
        {"photo_id": "b", "transfer_id": "t1", "shipment_id": "s1"},
        {"photo_id": "c", "transfer_id": "other", "shipment_id": None},
    ]
    assert photo_ids_to_link(rows, transfer_id="t1", shipment_id="s1", photo_ids=["a", "b", "a"]) == [
        "a",
        "b",
    ]
    with pytest.raises(PreparePhotoError):
        photo_ids_to_link(rows, transfer_id="t1", shipment_id="s2", photo_ids=["b"])
    with pytest.raises(PreparePhotoError):
        photo_ids_to_link(rows, transfer_id="t1", shipment_id="s1", photo_ids=["c"])


def test_prepare_photo_path():
    assert prepare_photo_path("t1", "p1", ".jpg") == "public/transfer/t1/p1.jpg"
