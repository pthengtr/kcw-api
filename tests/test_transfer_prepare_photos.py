import pytest

from src.transfer.photos import (
    PreparePhotoError,
    image_suffix,
    photo_ids_to_link,
    prepare_photo_path,
    remaining_photo_slots,
    shipment_photo_count,
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


def test_remaining_photo_slots_counts_only_linked_shipment():
    rows = [
        {"photo_id": "a", "shipment_id": "s1"},
        {"photo_id": "b", "shipment_id": "s1"},
        {"photo_id": "c", "shipment_id": "s2"},
        {"photo_id": "d", "shipment_id": None},
    ]
    assert shipment_photo_count(rows, shipment_id="s1") == 2
    assert remaining_photo_slots(rows, shipment_id="s1") == 6
    assert remaining_photo_slots(rows, shipment_id="s9") == 8
