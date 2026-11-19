# Quiet hours – an OpenVoiceOS PHAL plugin

The device turns its voice down in the evening and back up in the morning:
from 22:00 it remembers how loud it was and goes down to 20 %, and at 07:00
it goes back. It is a working plugin and a template for your own – made for
[Emkay](https://emkay.ai), and an ordinary OpenVoiceOS plugin, so it runs on
any OVOS device too.

**👉 The friendly guide: <https://dev.emkay.ai>**

## What a PHAL plugin is

A skill answers what people say. A **PHAL plugin** has no sentences: it
does one job for the device and talks to the rest of OpenVoiceOS only over
the messagebus. OpenVoiceOS' PHAL service starts every installed plugin
when OVOS starts, gives it the bus and its settings, and that's it.

This one shows the parts most plugins have:

- **Started with its settings** – `mycroft.conf`, under `PHAL` and the
  plugin's name:

  ```json
  "PHAL": {"ovos-phal-plugin-quiet-hours-example":
           {"start": "22:00", "end": "07:00", "volume": 20}}
  ```

- **Asking and telling over the bus** – `mycroft.volume.get` /
  `mycroft.volume.set`, the messages OVOS' volume plugins answer
  (ovos-PHAL-plugin-alsa on a Linux device, ovos-phal-plugin-browser in
  Emkay).
- **Telling the rest** – `ovos.quiet_hours.started` / `.ended`, so a skill
  can follow along, and an answer to `ovos.quiet_hours.status`.
- **Cleaning up** – `shutdown()` stops its timer and takes its handlers
  off the bus.
- **Found by its entry point** – `[project.entry-points."opm.phal"]` in
  `pyproject.toml` is how OpenVoiceOS finds it.

## Try it

Open it in [Emkay Dev](https://dev.emkay.ai) (VS Code with Emkay next to
the code): *Emkay: Run in Emkay* starts the plugin in Emkay and restarts it
each time you save; the output says which bus messages it handles. `pytest`
checks the clock arithmetic and the volume messages without OVOS running.

On an OVOS device: `pip install .` where OVOS' PHAL service runs, and
restart it.

## Try changing

- the times and how quiet it gets (`DEFAULTS`, or the settings above);
- what happens at quiet hours – dim the screen, or stop listening for the
  wake word (`mycroft.mic.mute`);
- a skill that asks `ovos.quiet_hours.status` and answers "is it quiet
  time?".

Plugins that need the device's hardware (sound cards, GPIO pins, system
services) can't run in a browser; ones like this, that only use the bus
and the network, can.
