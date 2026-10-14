import pytest
from PIL import Image


@pytest.fixture
def sample_png(tmp_path):
    """200x100 image: left half red, right half blue."""
    img = Image.new("RGB", (200, 100), (255, 0, 0))
    img.paste((0, 0, 255), (100, 0, 200, 100))
    path = tmp_path / "sample.png"
    img.save(path)
    return path
