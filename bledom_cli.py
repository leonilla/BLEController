import asyncio
import click
from bleak import BleakClient

# --- CONFIGURATION ---
# Replace with your actual MAC address
# Address can be found using the "scanner.py" script in the utils directory
ADDRESS = "FF:FF:10:97:CF:63"

class LEDController:
    def __init__(self, address):
        self.address = address

    async def send_command(self, hex_payload):
        """Connects to the device and sends the hex bytearray."""
        async with BleakClient(self.address) as client:
            if client.is_connected:
                print(f"Connected: {client.is_connected}")
                # Find write characteristic among the services the LED strip controller offers
                write_char = None
                for service in client.services:
                    for char in service.characteristics:
                        if "write-without-response" in char.properties:
                            write_char = char
                            break
                if write_char:
                    await client.write_gatt_char(write_char.uuid, bytes(hex_payload))
                    print(f"Sent: {hex_payload}")
                else:
                    print("Could not find a writeable characteristic.")
            else:
                print("Failed to connect to device.")

def hex_to_rgb(hex_str):
    """Converts #RRGGBB or RRGGBB to a list of 3 integers."""
    hex_str = hex_str.lstrip('#')
    return [int(hex_str[i:i+2], 16) for i in (0, 2, 4)]

# --- CLI COMMANDS ---

@click.command()
@click.option('--on', is_flag=True, help='Turn the lights ON')
@click.option('--off', is_flag=True, help='Turn the lights OFF')
@click.option('--color', type=str, help='Set color in Hex (e.g., FF0000 for Red)')
@click.option('--bright', type=int, help='Set brightness (0-100)')

def main(on, off, color, bright):
    """Simple CLI for controlling Bluetooth LED strips."""
    controller = LEDController(ADDRESS)

    # 1. Power Logic (Command 04)
    if on: 
        # 7e 04 04 01 00 01 ff 00 ef       
        cmd = [0x7e, 0x04, 0x04, 0x01, 0x00, 0x01, 0xff, 0x00, 0xef]
        asyncio.run(controller.send_command(cmd))
    elif off:
        # 7e 04 04 01 00 00 ff 00 ef
        cmd = [0x7e, 0x04, 0x04, 0x01, 0x00, 0x00, 0xff, 0x00, 0xef]
        asyncio.run(controller.send_command(cmd))

    # 2. Color Logic (Command 05)
    if color:
        r, g, b = hex_to_rgb(color)
        # 7e 07 05 03 ff 00 00 00 ef
        cmd = [0x7e, 0x07, 0x05, 0x03, r, g, b, 0x00, 0xef]
        asyncio.run(controller.send_command(cmd))

    # 3. Brightness Logic (Command 01)
    if bright is not None:
        # Constrain 0-100 and send
        val = max(0, min(100, bright))
        # 7e 04 01 0a 00 00 00 00 ef
        cmd = [0x7e, 0x04, 0x01, val, 0x00, 0x00, 0x00, 0x00, 0xef]
        asyncio.run(controller.send_command(cmd))

if __name__ == "__main__":
    main()