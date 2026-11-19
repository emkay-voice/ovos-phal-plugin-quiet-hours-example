"""Quick checks that run without OpenVoiceOS running: `pytest`.

Running the plugin is the real test - in Emkay (Emkay: Run in Emkay) or
on an OVOS device - but these catch the usual slips early.
"""
import sys
from datetime import time
from pathlib import Path

from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus

sys.path.insert(0, str(Path(__file__).parent.parent))
import ovos_phal_plugin_quiet_hours_example as pkg  # noqa: E402


def test_quiet_hours_past_midnight():
    start, end = time(22, 0), time(7, 0)
    assert pkg.is_quiet(time(23, 30), start, end)
    assert pkg.is_quiet(time(3, 0), start, end)
    assert not pkg.is_quiet(time(7, 0), start, end)
    assert not pkg.is_quiet(time(12, 0), start, end)


def test_quiet_hours_in_the_day():
    assert pkg.is_quiet(time(14, 0), time(13, 0), time(15, 0))
    assert not pkg.is_quiet(time(16, 0), time(13, 0), time(15, 0))


def make(config):
    bus = FakeBus()
    sent = []
    bus.on("message", lambda m: sent.append(m if isinstance(m, str) else m.serialize()))
    plugin = pkg.QuietHoursPlugin(bus=bus, config=config)
    return plugin, bus, sent


def test_turns_down_and_back_up():
    # quiet all day, so it begins at once
    plugin, bus, sent = make({"start": "00:00", "end": "23:59", "volume": 15})
    try:
        assert plugin.quiet
        bus.emit(Message("mycroft.volume.get.response", {"percent": 0.7}))
        assert any('"mycroft.volume.set"' in s and '"percent": 0.15' in s for s in sent)
        plugin.finish()
        assert any('"mycroft.volume.set"' in s and '"percent": 0.7' in s for s in sent)
    finally:
        plugin.shutdown()


def test_answers_status():
    plugin, bus, sent = make({"start": "22:00", "end": "07:00"})
    try:
        answers = []
        bus.on("ovos.quiet_hours.status.response", lambda m: answers.append(m.data))
        bus.emit(Message("ovos.quiet_hours.status"))
        assert answers and answers[0]["start"] == "22:00" and answers[0]["end"] == "07:00"
    finally:
        plugin.shutdown()
