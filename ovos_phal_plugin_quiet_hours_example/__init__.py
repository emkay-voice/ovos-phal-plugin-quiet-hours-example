"""Quiet hours: the device turns its voice down in the evening and back up in the morning.

A PHAL plugin: it has no sentences and no intents. OpenVoiceOS' PHAL service
starts it when OVOS starts (Emkay Dev starts it from your files), gives it
the messagebus and its settings, and it does its job on the bus:

- every minute it looks at the clock; when quiet hours begin it asks the
  device how loud it is (mycroft.volume.get), remembers that and turns it
  down (mycroft.volume.set). When they end, it turns it back up.
- it tells the rest of OVOS (ovos.quiet_hours.started / .ended), so a skill
  can do the same, and answers ovos.quiet_hours.status with whether it is
  quiet now.

The volume messages are OVOS' own: ovos-PHAL-plugin-alsa answers them on a
Linux device, ovos-phal-plugin-browser in Emkay. That is what a PHAL plugin
is for: one plugin for one job, talking to the rest only over the bus.

Its settings are in mycroft.conf, under PHAL and the plugin's name:

    "PHAL": {"ovos-phal-plugin-quiet-hours-example":
             {"start": "22:00", "end": "07:00", "volume": 20}}

Try changing: the times and how quiet (DEFAULTS), or what happens when it
gets quiet – dim the screen too, or stop listening for the wake word.
"""
import threading
from datetime import datetime, time as clock

from ovos_bus_client.message import Message
from ovos_plugin_manager.templates.phal import PHALPlugin

#: used when mycroft.conf says nothing: 22:00 to 07:00, at 20 % volume
DEFAULTS = {"start": "22:00", "end": "07:00", "volume": 20}
EVERY = 60   # seconds between looks at the clock


def parse(hhmm):
    """"22:00" -> time(22, 0)."""
    hours, minutes = (int(x) for x in str(hhmm).split(":"))
    return clock(hours, minutes)


def is_quiet(now, start, end):
    """Is `now` (a time) inside quiet hours? They may run past midnight."""
    if start <= end:                  # e.g. 13:00-15:00
        return start <= now < end
    return now >= start or now < end  # e.g. 22:00-07:00


class QuietHoursPlugin(PHALPlugin):

    def __init__(self, bus=None, name="ovos-phal-plugin-quiet-hours-example", config=None):
        super().__init__(bus=bus, name=name, config=config)
        settings = {**DEFAULTS, **(self.config or {})}
        self.start_at, self.end_at = parse(settings["start"]), parse(settings["end"])
        self.quiet_volume = int(settings["volume"])
        self.quiet = False
        self.volume_before = None   # how loud it was before quiet hours (0..1)
        self._timer = None
        # the messages it handles (shutdown() takes them off again)
        self.handlers = [("ovos.quiet_hours.status", self.on_status),
                         ("mycroft.volume.get.response", self.on_volume)]
        for topic, handler in self.handlers:
            self.bus.on(topic, handler)
        self.check()

    def check(self):
        """Look at the clock; start or end quiet hours; look again in a minute."""
        quiet_now = is_quiet(datetime.now().time(), self.start_at, self.end_at)
        if quiet_now and not self.quiet:
            self.begin()
        elif self.quiet and not quiet_now:
            self.finish()
        self._timer = threading.Timer(EVERY, self.check)
        self._timer.daemon = True
        self._timer.start()

    def begin(self):
        self.quiet = True
        self.log.info(f"{self.name}: quiet hours begin ({self.start_at:%H:%M}-{self.end_at:%H:%M})")
        # ask how loud it is; on_volume remembers it and turns it down
        self.bus.emit(Message("mycroft.volume.get"))
        self.bus.emit(Message("ovos.quiet_hours.started"))

    def on_volume(self, message):
        """The device says how loud it is: remember it, then turn it down."""
        if self.quiet and self.volume_before is None:
            self.volume_before = message.data.get("percent")
            self.bus.emit(Message("mycroft.volume.set",
                                  {"percent": self.quiet_volume / 100, "play_sound": False}))

    def finish(self):
        self.quiet = False
        self.log.info(f"{self.name}: quiet hours end")
        if self.volume_before is not None:
            self.bus.emit(Message("mycroft.volume.set",
                                  {"percent": self.volume_before, "play_sound": False}))
        self.volume_before = None
        self.bus.emit(Message("ovos.quiet_hours.ended"))

    def on_status(self, message):
        self.bus.emit(message.response({
            "quiet": self.quiet,
            "start": f"{self.start_at:%H:%M}", "end": f"{self.end_at:%H:%M}",
            "volume": self.quiet_volume}))

    def shutdown(self):
        """Stopped (or restarted by Emkay Dev): no more looks at the clock."""
        if self._timer:
            self._timer.cancel()
        if self.quiet:
            self.finish()
        for topic, handler in self.handlers:
            self.bus.remove(topic, handler)
        super().shutdown()
