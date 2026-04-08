# BLEController
Control utilities for ELK-BLEDOM LED strips.

ELK-BLEDOM LED Strips are widely popular.\
Manufacturers provide Android and Apple apps for controlling the strips remotely.\
These apps use a proprietary protocol to communicate with the strip controller over Low Energy Bluetooth (BLE).\
Sending messages using this proprietary protocol allows for the lights to be controlled from other devices (for more information about the protocol messages, see BLEDOM_PROTOCOL.md)

## Usage

### Installation
Python 3 required.\
Install dependencies:\
`python -m pip install click bleak customtkinter`

### utils/scanner.py
Utility that uses bleak to scan for nearby BLE devices and lists them along with their physical address.
Use this utility to find your strip's MAC address. You'll need it to establish a connection.

### bledom_cli.py
Command line interface, ideal for sending individual messages.

Replace the `ADDRESS` in the script with your strip's actual MAC address.\
Run `python bledom_cli.py` with options `--on`, `--off`, `--color RGB`, or `--bright int` to send the corresponding message to the light strip.\
The client will establish a connection, send the message, and shut down.

### bledom_gui.py
Basic control panel: turn the lights on/off, change color, change brightness.


Run `python bledom_gui.py` to launch the control window.\
Input the ELK-BLEDOM's MAC address and click connect.\
By default, the window will remember the MAC address and attempt a connection on launch. If this is not desired, uncheck the corresponding box.\
Once the connection has been established, use the buttons to control the lights.
