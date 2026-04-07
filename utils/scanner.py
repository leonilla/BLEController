import asyncio
from bleak import BleakScanner

async def scan():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    for d in devices:
        # Look for "ELK-BLEDOM" or "Triones" in the output
        print(f"Address: {d.address}, Name: {d.name}")

asyncio.run(scan())