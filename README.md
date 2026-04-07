# BLEController
Control utilities for ELK-BLEDOM LED strips.

ELK-BLEDOM LED Strips are popular due to their wide availability and friendly prices.
The manufacturer provides Android and Apple apps for controlling the strips remotely.
These apps make use of a proprietary protocol to communicate with the strip controller over Low Energy Bluetooth (BLE).
Reverse-engineering the protocol based off the messages an Android device sent to it revealed:

- ## General Message Format:
 7e [LEN] [CMD] [R] [G] [B] 00 ef

- ## SET STATE Message: 7e 04 04 01 00 [STATE] ff 00 ef
OFF : 7e 04 04 01 00 00 ff 00 ef	(6th byte = 00)
ON  : 7e 04 04 01 00 01 ff 00 ef	(6th byte = 01)

- ## SET COLOR Message : 7e 07 05 [R] [G] [B] 00 ef
RED : 7e 07 05 03 ff 00 00 00 ef	RGB = FF 00 00
GRN : 7e 07 05 03 00 ff 00 00 ef	RGB = 00 FF 00
BLU : 7e 07 05 03 00 00 ff 00 ef	RGB = 00 00 FF
WHT : 7e 07 05 03 ff ff ff 00 ef	RGB = FF FF FF

- ## SET BRIGHT Message: 7e 04 01 [VALUE] 00 00 00 ef
10% : 7e 04 01 0a 00 00 00 00 ef --> 10% brightness (4th byte = 0a)
99% : 7e 04 01 63 00 00 00 00 ef --> 99% brightness (4th byte = 63)
