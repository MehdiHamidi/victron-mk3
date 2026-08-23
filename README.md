# victron-mk3

A Python library for communicating with certain Victron charger and inverter
devices that have VE.Bus ports using the Victron Interface MK3-USB (VE.Bus to USB).

This library provides functions to allow the host computer to act as a remote
control panel for the device. It can monitor the status and performance of
the device and set remote panel switch state and current limits.

See also the [Home Assistant integration](https://github.com/MehdiHamidi/victron-mk3-hass) based
on this library.

## Compatibility

This library has been tested with the following devices:

- Victron Multiplus
- Victron Multiplus II

Please inform the author if you test this library with other potentially compatible
devices.

## Command line interface

This repository includes a simple tool for testing the behavior of the MK3 interface.

Before running the CLI, install the required packages.

```
pip install -r requirements.txt
```

After attaching the MK3 interface, determine the path of the serial port device
to include on the command-line. In these examples, it is `tty.usbserial-HQ2217T743W`
but yours may be different depending on your platform.  On Windows, the serial port
may be `COM1` or something similar.

### Monitor the status of an attached device

The following command continuously queries and displays the status of the LEDs, the charger,
the inverter, and control panel configuration until stopped.

```
python3 cli.py monitor /dev/tty.usbserial-HQ2217T743W
```

<details>
<summary>Example monitor command output</summary>

```
VersionResponse
  version: 1170216
InterfaceResponse
  flags: PANEL_DETECT|UNDOCUMENTED_04
LEDResponse
  on: MAINS|FLOAT
  blink: OFF
DCResponse
  dc_voltage: 13.77
  dc_current_to_inverter: 0.0
  dc_current_from_charger: 1.4000000000000001
  ac_inverter_frequency: 60.09
ACResponse
  ac_phase: 1
  ac_num_phases: 1
  device_state: STATE_CHARGE
  ac_mains_voltage: 119.46000000000001
  ac_mains_current: 1.48
  ac_inverter_voltage: 119.46000000000001
  ac_inverter_current: 0.91
  ac_mains_frequency: 60.31
ACResponse
  ac_phase: 2
  ac_num_phases: 0
  device_state: STATE_CHARGE
  ac_mains_voltage: 0.55
  ac_mains_current: 0.0
  ac_inverter_voltage: 119.46000000000001
  ac_inverter_current: 0.0
  ac_mains_frequency: 60.31
PowerResponse
  dc_power: 20
  ac_mains_power: 40
  ac_inverter_power: 20
ConfigResponse
  last_active_ac_input: 0
  current_limit_overridden_by_panel: True
  digital_multi_control_dedicated: False
  num_ac_inputs: 1
  remote_panel_detected: True
  minimum_current_limit: 9.4
  maximum_current_limit: 50.0
  actual_current_limit: 50.0
  switch_register: DIRECT_REMOTE_SWITCH_CHARGE|DIRECT_REMOTE_SWITCH_INVERT|FRONT_SWITCH_UP|SWITCH_CHARGE|SWITCH_INVERT|ONBOARD_REMOTE_SWITCH_INVERT
```
</details>

### Set the remote panel switch state and current limit

The following command sets the remote panel switch state to `on` and the current limit to its maximum.
This is the default setting.

```
python3 cli.py control /dev/tty.usbserial-HQ2217T743W on
```

The following command sets the remote panel switch state to `charger_only` and the current limit to 12.5 amps
and continues monitoring indefinitely.

```
python3 cli.py control /dev/tty.usbserial-HQ2217T743W charger_only --current-limit 12.5 --monitor
```

The following command sets the remote panel switch state to `off` and activates [standby mode](#standby-mode) to prevent the
interface from becoming unresponsive while the device is off.

```
python3 cli.py control /dev/tty.usbserial-HQ2217T743W off --standby
```

Here's what each remote panel switch state means:

- `on`: Enable the charger and enable the inverter.
- `charger_only`: Enable the charger and disable the inverter.
- `inverter_only`: Enable the inverter and disable the charger.
- `off`: Disable the charger and disable the inverter.

The front panel switch and other inputs on the device may override the remote panel switch state.

- When the device is turned off by the front panel switch or by the remote on/off connection, neither the charger nor the inverter will operate.
- When the device is forced to charge only mode using the front panel switch, the inverter will not operate regardless of the remote panel switch state set by this interface.
- Other conditions determined by the device may also apply such as constraints on the mains voltage and battery state of charge.

The device retains the remote panel switch state and current limit set by the MK3 interface even after it has been disconnected from VE.Bus until the device goes to sleep (assuming it is not on standby). To restore the device to its default behavior, set the remote panel mode to `on` and set the current limit to its maximum.

<details>
<summary>Example control command output</summary>

```
Setting switch state to ON and current limit to None amps
VersionResponse
  version: 1170216
StateResponse
InterfaceResponse
  flags: PANEL_DETECT
StateResponse
ConfigResponse
  last_active_ac_input: 0
  current_limit_overridden_by_panel: True
  digital_multi_control_dedicated: False
  num_ac_inputs: 1
  remote_panel_detected: True
  minimum_current_limit: 0.0
  maximum_current_limit: 50.0
  actual_current_limit: 30.0
  switch_register: DIRECT_REMOTE_SWITCH_CHARGE|FRONT_SWITCH_UP|SWITCH_CHARGE|ONBOARD_REMOTE_SWITCH_INVERT
VersionResponse
  version: 1170216
```
</details>

### Probe whether a device is attached to the interface and operational

The following command attempts to connect to a device using the interface and reports whether
it is operational or the reason it was unable to connect.

```
python3 cli.py probe /dev/tty.usbserial-HQ2217T743W
```

<details>
<summary>Example probe command output</summary>

```
Result: OK
```
</details>

## Standby mode

When the charger/inverter device is turned off and standby mode is not enabled, it may go to sleep and shut off its internal power supply to avoid draining the batteries. Because the MK3 interface is powered from the device's VE.Bus port, then the interface will lose power when the device is turned off and it will be unable to send a command to wake the device up again.

The solution is to enable standby mode. When standby mode is enabled, the MK3 interface will prevent the device from going to sleep as long as it remains connected to the device's VE.Bus. Note that the device draws more energy from the batteries while in standby than it would while sleeping.

We recommend always enabling standby mode to maintain control of the device at all times.

## Troubleshooting

### What to do if your charger/inverter turned itself off and won't turn on anymore (and the front panel switch doesn't work)

Don't panic!

Your device probably thinks it's supposed to be sleeping and it needs little nudge to wake up or forget that it's supposed to be sleeping. The device firmware determines the operating mode based on several factors, including the state of the front panel switch, remote panel state (set via the MK3 interface), and remote on/off connection. You might feel concerned that toggling the front panel switch doesn't fix the problem right away and it's probably going to be fine.

Here are some possible recovery methods:

- Check the front panel status indicators on the device. If some of indicators are lit, they may tell you what the problem is.
- If you have connected a switch to the remote on/off switch input of your device, make sure it's in the ON position and that the wires are intact.
- Plug the device into AC mains. The device should wake up within a few seconds and begin responding to the MK3 interface again. Use the MK3 interface to set the remote panel mode to ON.
- Unplug the MK3 interface from the VE.Bus port or disconnect the ethernet jack from the interface. Toggle the front panel switch to OFF. Wait at least 30 seconds for the device to fully go to sleep. Toggle the front panel switch to ON and wait a few seconds for the device to turn on. If that didn't work, try toggling the front panel switch to CHARGE ONLY then OFF, wait at least 30 seconds again, then ON again. Plug the MK3 interface back in as before.
- Ensure the device is connected to the batteries and receiving power.

Once you have resolved the issue, consider enabling [standby mode](#standby-mode) to prevent the device from falling asleep unintentionally.

### What to do if the MK3 interface has difficulties communicating with your charger/inverter device

Here are some things to try if the MK3 interface appears to be having difficulties communicating with your charger/inverter device or is outputting incomplete data:

- Check the logs for relevant messages.
- Ensure that the MK3 interface is plugged into USB and the path of the serial port is correct.
- The MK3 interface receives power from VE.Bus and will not operate if the device is asleep. Ensure it is plugged into VE.Bus and awake as explained in [this topic](#what-to-do-if-your-chargerinverter-turned-itself-off-and-wont-turn-on-anymore-and-the-front-panel-switch-doesnt-work).
- Unplug the MK3 interface from your computer's USB port, unplug the MK3 interface from the device's VE.Bus (or disconnect the ethernet jack from the interface), plug the MK3 back in as before, and try again.
- If you have connected additional peripherals to your device's VE.Bus ports, try unplugging them to rule out possible conflicts with the MK3 interface.
- If you just operated your MK3 interface using a different program such as the Victron Connect app, the interface may have been left in a state that this library doesn't know how to handle. Quit the other program, unplug the MK3 from VE.Bus to reset it, plug it back in, and try again.
- Try using the MK3 interface with Victron Connect, just to make sure it works, and to apply firmware updates to the device.

## Build for distribution

```
pip install setuptools build
python3 -m build
```

## References

This library implements the MK2/MK3 protocol according to the following references.

Victron documentation: [Interfacing with VE.Bus products – MK2 Protocol](https://www.victronenergy.com/upload/documents/Technical-Information-Interfacing-with-VE-Bus-products-MK2-Protocol-3-14.pdf)

Victron community [forum post](https://community.victronenergy.com/questions/1096/mk3-usb-s-state-command-does-not-change-panel-swit.html) about how to control standby mode:

> For the MK3 the jumpers were replaced by software control of the VE.Bus standby and panel detect lines.
> Unfortunately this was not mentioned in the "Interfacing with VE.Bus products - MK2 Protocol" documentation.
> We will add it.
>
> To get you going, here is the command description.
>
> Command: 'H' \<Line state\>
>
> Reply: 'H' \<Line state\>
>
> \<Line state\> is specified as follows. Setting a bit pulls the line to GND
>
> | Bit number | Meaning      |
> | ---------- | ------------ |
> |          0 | Panel detect |
> |          1 | Standby      |
>
> The above command is supported by the MK3 only.
> Please note that the MK3 chip in the USB dongle is powered through the VE.Bus, when loosing VE.Bus power
> the above lines will become floating again.
