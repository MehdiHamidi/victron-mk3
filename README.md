# victron-mk3

A Python library for communicating with certain Victron charger and inverter
devices that have VE.Bus ports using the Victron Interface MK3-USB (VE.Bus to USB).

This library provides functions to allow the host computer to act as a remote
control panel for the device. It can monitor the status and performance of
the device and set remote switch state and current limits.

See also the [Home Assistant integration](https://github.com/j9brown/victron-mk3-hacs) based
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

### Set the remote switch state and current limit

The following command sets the remote switch state to `on` and the current limit to its maximum.
This is the default setting.

```
python3 cli.py control /dev/tty.usbserial-HQ2217T743W on
```

The following command sets the remote switch state to `charger_only` and the current limit to 12.5 amps
and continues monitoring indefinitely.

```
python3 cli.py control /dev/tty.usbserial-HQ2217T743W charger_only --current-limit 12.5 --monitor
```

The following command sets the remote switch state to `off` and activates standby mode and to prevent the
interface from becoming unresponsive while the device is off. Refer to the standby section for
more details.

```
python3 cli.py control /dev/tty.usbserial-HQ2217T743W off --standby
```

Here's what each remote switch state means:

- `on`: Enable the charger and enable the inverter.
- `charger_only`: Enable the charger and disable the inverter.
- `inverter_only`: Enable the inverter and disable the charger.
- `off`: Disable the charger and disable the inverter.

The front panel switch and other inputs on the device may override the remote switch state.

- When the device is turned off by the front panel switch or by the remote on/off connection,
  neither the charger nor the inverter will operate.
- When the device is forced to charge only mode using the front panel switch, the inverter
  will not operate regardless of the remote switch state set by this interface.
- Other conditions determined by the device may also apply such as constraints on the
  mains voltage and battery state of charge.

The device retains the remote switch state and current limit set by the MK3 interface even after
it has been disconnected from VE.Bus until the device goes to sleep (assuming it is not on standby).

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

## Standby

When the device is turned off, it may go to sleep and shut off its internal power supply
to avoid draining the batteries. Because the MK3 interface is powered from device's VE.Bus
port, it too will lose power and it will become unresponsive. Consequently, you will not
be able to turn the device back on again using the interface.

Don't panic!

There are two ways to resolve this issue:

- When standby mode is enabled, the interface will prevent the device from going to sleep
  as long as it remains connected to the device's VE.Bus. Note that the device draws more energy
  from the batteries while in standby than it would while sleeping.
- The device will automatically wake up from sleep whenever power is supplied to its AC input.

So if the device is asleep and it is not responding to the MK3 interface, just plug it into
the AC mains to wake it up. Try sending the command again and consider enabling standby mode.

## Build for distribution

```
pip install setuptools build
python3 -m build
```

## Troubleshooting

Here are some things to try if the MK3 interface appears to be having difficulties communicating with your inverter:

- Unplug the MK3 from your computer's USB port and from the device's VE.Bus, plug it back in, and try again.
- Check whether your device is remotely turned off and sleeping.  Consider enabling [standby](#standby) mode.
- If there are additional peripherals plugged into your device's VE.Bus ports, try unplugging them to check for conflicts with the MK3 interface.
- If you just operated your MK3 interface with a different program such as the Victron Connect app, the interface may have been left in a state that this library doesn't know how to handle.  Quit the other program, unplug the MK3 from VE.Bus to reset it, plug it back in, and try again.

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
