## General Message Format:
 7e [LEN] [CMD] [R] [G] [B] 00 ef

## SET STATE Message: 7e 04 04 01 00 [STATE] ff 00 ef
OFF : 7e 04 04 01 00 00 ff 00 ef	(6th byte = 00)
ON  : 7e 04 04 01 00 01 ff 00 ef	(6th byte = 01)

## SET COLOR Message : 7e 07 05 [R] [G] [B] 00 ef
RED : 7e 07 05 03 ff 00 00 00 ef	RGB = FF 00 00
GRN : 7e 07 05 03 00 ff 00 00 ef	RGB = 00 FF 00
BLU : 7e 07 05 03 00 00 ff 00 ef	RGB = 00 00 FF
WHT : 7e 07 05 03 ff ff ff 00 ef	RGB = FF FF FF

## SET BRIGHT Message: 7e 04 01 [VALUE] 00 00 00 ef
10% : 7e 04 01 0a 00 00 00 00 ef --> 10% brightness (4th byte = 0a)
99% : 7e 04 01 63 00 00 00 00 ef --> 99% brightness (4th byte = 63)

## Disclaimer
Further/Unlisted messages are part of the protocol (OPCodes that are not 01, 04 or 05).
They control the module's additional modes ("Rainbow Jump", "Red Strobe", etc.)
If you figure out the syntax for triggering these modes, feel free to add it to this file.
