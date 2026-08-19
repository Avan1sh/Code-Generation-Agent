import pytest
from pydantic import ValidationError

from solution import Playlist


def test_valid():
    p = Playlist(name="mix", tracks=["a", "b"])
    assert p.tracks == ["a", "b"]


def test_boundaries_accepted():
    assert len(Playlist(name="m", tracks=["a"]).tracks) == 1
    assert len(Playlist(name="m", tracks=["a", "b", "c"]).tracks) == 3


def test_empty_rejected():
    with pytest.raises(ValidationError):
        Playlist(name="m", tracks=[])


def test_too_many_rejected():
    with pytest.raises(ValidationError):
        Playlist(name="m", tracks=["a", "b", "c", "d"])
