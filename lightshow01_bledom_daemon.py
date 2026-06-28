import asyncio
import argparse
from bleak import BleakClient

def parse_arguments():
    """Parses explicit required command line arguments for the daemon."""
    parser = argparse.ArgumentParser(
        description="Persistent background BLE LED UDP ingestion daemon."
    )
    parser.add_argument(
        "--address",
        type=str,
        required=True,
        help="The unique hardware MAC address of your target BLE LED device (e.g., FF:FF:10:97:CF:63)."
    )
    parser.add_argument(
        "--ip",
        type=str,
        required=True,
        help="The local interface network IP address to bind the UDP server to (e.g., 0.0.0.0 or 127.0.0.1)."
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="The network port number to listen on for incoming lighting data frames (e.g., 5005)."
    )
    return parser.parse_args()

class PersistentLEDController:
    def __init__(self, address):
        self.address = address
        self.queue = asyncio.Queue()
        self.client = None
        self.write_char = None

    async def find_write_characteristic(self):
        """Discovers the services and caches the correct write characteristic."""
        for service in self.client.services:
            for char in service.characteristics:
                if "write-without-response" in char.properties:
                    return char
        return None

    async def connection_manager(self):
        """Maintains a persistent connection and processes the queue."""
        print(f"Connecting to {self.address}...")
        try:
            async with BleakClient(self.address) as client:
                self.client = client
                if client.is_connected:
                    print("Connected! Discovering characteristics...")
                    self.write_char = await self.find_write_characteristic()
                    
                    if not self.write_char:
                        print("Error: Could not find a writeable characteristic.")
                        return

                    print("Ready to process audio frames. Send data via UDP!")
                    
                    # Main consumer loop
                    packet_count = 0
                    while True:
                        payload = await self.queue.get()
                        try:
                            await client.write_gatt_char(self.write_char.uuid, bytes(payload))
                            packet_count += 1
                            print(f"Streaming Active | Ingested Queue Size: {self.queue.qsize()} | BLE Packets Sent: {packet_count}   ", end="\r")
                        except Exception as e:
                            print(f"\nFailed to send BLE packet: {e}")
                        finally:
                            self.queue.task_done()
                else:
                    print("Failed to establish BLE connection.")
        except Exception as e:
            print(f"BLE connection manager crashed: {e}")

class UDPServerProtocol(asyncio.DatagramProtocol):
    """Protocol to ingest incoming network packets and push them to the BLE queue."""
    def __init__(self, queue):
        self.queue = queue

    def datagram_received(self, data, addr):
        try:
            self.queue.put_nowait(data)
        except asyncio.QueueFull:
            # Drop frames if the BLE link can't keep up with the audio analyzer
            pass

async def main():
    args = parse_arguments()
    
    ADDRESS = args.address
    UDP_IP = args.ip
    UDP_PORT = args.port

    controller = PersistentLEDController(ADDRESS)

    # Start the BLE connection manager task
    ble_task = asyncio.create_task(controller.connection_manager())

    # Start the local UDP server to listen for audio mapping script
    loop = asyncio.get_running_loop()
    print(f"Starting local UDP server on {UDP_IP}:{UDP_PORT}...")
    
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPServerProtocol(controller.queue),
            local_addr=(UDP_IP, UDP_PORT)
        )
    except Exception as e:
        print(f"Critical Error binding UDP interface: {e}")
        ble_task.cancel()
        return

    try:
        await ble_task
    except asyncio.CancelledError:
        print("\nShutting down stream...")
    finally:
        transport.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDaemon closed manually.")