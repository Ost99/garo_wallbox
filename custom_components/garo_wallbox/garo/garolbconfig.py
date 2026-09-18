from . import utils


class GaroLBConfig:
    """Holds load-balancing current limits from the lbconfig endpoint."""

    def __init__(self, json=None):
        self._fuse = 0
        self._fuse101 = 0
        self._has_changed = False
        self.load(json)

    def load(self, json=None) -> bool:
        self._has_changed = False

        if not json:
            return False

        self.fuse = utils.read_value(
            json,
            'loadBalancingFuse',
            self._fuse,
        )

        self.fuse101 = utils.read_value(
            json,
            'loadBalancingFuse101',
            self._fuse101,
        )

        return self._has_changed

    @property
    def has_changed(self):
        return self._has_changed

    @property
    def fuse(self):
        """Current limit (A) for load-balancing meter 100."""
        return self._fuse

    @fuse.setter
    def fuse(self, value):
        if self._fuse == value:
            return

        self._fuse = value
        self._has_changed = True

    @property
    def fuse101(self):
        """Current limit (A) for load-balancing meter 101."""
        return self._fuse101

    @fuse101.setter
    def fuse101(self, value):
        if self._fuse101 == value:
            return

        self._fuse101 = value
        self._has_changed = True