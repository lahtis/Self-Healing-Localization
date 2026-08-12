import shl
from shl._version import (
    __version__ as version_from_module,
)


def test_version_is_consistent():
    assert shl.__version__ == version_from_module


def test_package_metadata():
    assert isinstance(shl.__version__, str)
    assert shl.__version__
