"""Test helper: the archived-channels file is not in the repo, so thumbnail tests
replace the archive lookup with an empty list when the file is missing."""
import os
from unittest import mock

import channels


def _archive_path():
    rel = channels.load_channel_config().get("archived_channels_file")
    return os.path.join(channels.ROOT, rel) if rel else None


_patchers = []


def start():
    path = _archive_path()
    if path and os.path.exists(path):
        return
    for target in ("channels.load_archived_channels", "playlists.load_archived_channels"):
        try:
            p = mock.patch(target, return_value=[])
            p.start()
            _patchers.append(p)
        except (ImportError, AttributeError):
            pass


def stop():
    while _patchers:
        _patchers.pop().stop()
