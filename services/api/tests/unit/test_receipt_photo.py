"""Bound image cost and strip camera metadata without cropping visible receipt facts."""

import io

import pytest
from PIL import Image


def test_camera_photo_is_oriented_resized_and_has_no_exif():
    from app.providers.openai_receipt import prepare_photo

    photo = Image.new("RGB", (2400, 3200), "white")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "private camera metadata"
    raw = io.BytesIO()
    photo.save(raw, format="JPEG", exif=exif)
    ready = Image.open(io.BytesIO(prepare_photo(raw.getvalue())))
    assert ready.size == (1600, 1200)
    assert ready.format == "JPEG"
    assert not ready.getexif()


def test_corrupt_photo_is_rejected_before_any_model_request():
    from app.providers.errors import ProviderUnavailable
    from app.providers.openai_receipt import prepare_photo

    with pytest.raises(ProviderUnavailable):
        prepare_photo(b"\xff\xd8\xffnot a real photo")
