import asyncio
import threading
import json
import os
import customtkinter as ctk
from tkinter import colorchooser
from bleak import BleakClient

# --- CONFIGURATION & CONSTANTS ---
CONFIG_FILE = "config.json"

class LEDLogic:
    """Handles the Background Bluetooth Thread and Bleak communication."""
    def __init__(self, app):
        self.app = app
        self.write_char = None
        self.client = None
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _connect(self, address):
        try:
            self.client = BleakClient(address)
            await self.client.connect()
            if self.client.is_connected:
                print(f"Connected: {self.client.is_connected}")
                # Find write characteristic among the services the LED strip controller offers
                for service in self.client.services:
                    for char in service.characteristics:
                        if "write-without-response" in char.properties:
                            self.write_char = char
                            print(f"Set found writeable characteristic {self.write_char.uuid}.")
                            break
                if self.write_char is None:
                    print("Could not find a writeable characteristic.")
                    # TODO: Failing to find the Characteristic should trigger exception
                else:
                    self.app.update_status("Connected successfully.")
                    self.app.on_connection_success()
            
        except Exception as e:
            self.app.update_status(f"Connection Error: {e}")
            self.app.on_connection_fail()

    async def _send(self, payload):
        if self.client and self.client.is_connected:
            try:
                await self.client.write_gatt_char(self.write_char, bytes(payload))
                self.app.update_status(f"Sent: {bytes(payload).hex(' ')}")
            except Exception as e:
                self.app.update_status(f"Send Error: {e}")

    def connect(self, address):
        asyncio.run_coroutine_threadsafe(self._connect(address), self.loop)

    def send(self, payload):
        asyncio.run_coroutine_threadsafe(self._send(payload), self.loop)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LED Controller Pro")
        self.geometry("400x550")
        self.logic = LEDLogic(self)

        # UI State
        self.is_on = True
        self.current_rgb = (255, 0, 0)
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # --- PANEL 1: CONFIGURATION ---
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=0, column=0, padx=20, pady=10, sticky="nsew")
        
        ctk.CTkLabel(self.config_frame, text="MAC Address:", font=("Arial", 12, "bold")).pack(pady=(10,0))
        self.mac_entry = ctk.CTkEntry(self.config_frame, placeholder_text="XX:XX:XX:XX:XX:XX", width=250)
        self.mac_entry.pack(pady=5)

        self.launch_check = ctk.CTkCheckBox(self.config_frame, text="Connect on launch")
        self.launch_check.pack(pady=5)

        self.conn_btn = ctk.CTkButton(self.config_frame, text="Connect", command=self.attempt_connection)
        self.conn_btn.pack(pady=10)

        self.status_indicator = ctk.CTkLabel(self.config_frame, text="● Disconnected", text_color="red")
        self.status_indicator.pack(pady=5)

        # --- PANEL 2: CONTROLS ---
        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        # Power Switch
        self.power_switch = ctk.CTkSwitch(self.ctrl_frame, text="Power", command=self.toggle_power)
        self.power_switch.select()
        self.power_switch.pack(pady=15)

        # Color Picker Button
        self.color_btn = ctk.CTkButton(self.ctrl_frame, text="Select Color", fg_color="#ff0000", command=self.pick_color)
        self.color_btn.pack(pady=15)

        # Brightness Slider
        ctk.CTkLabel(self.ctrl_frame, text="Brightness").pack()
        self.bright_slider = ctk.CTkSlider(self.ctrl_frame, from_=0, to=100, command=self.update_brightness)
        self.bright_slider.set(100)
        self.bright_slider.pack(pady=(0, 20))

        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w", fg_color="gray20")
        self.status_bar.grid(row=2, column=0, sticky="ew")

        self.lock_controls()

    # --- LOGIC METHODS ---

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                self.mac_entry.insert(0, data.get("mac", ""))
                if data.get("auto", False):
                    self.launch_check.select()
                    self.after(1000, self.attempt_connection)

    def save_settings(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"mac": self.mac_entry.get(), "auto": self.launch_check.get()}, f)

    def lock_controls(self):
        for child in self.ctrl_frame.winfo_children():
            child.configure(state="disabled")

    def unlock_controls(self):
        for child in self.ctrl_frame.winfo_children():
            child.configure(state="normal")

    def attempt_connection(self):
        mac = self.mac_entry.get()
        if not mac: return
        self.update_status("Connecting...")
        self.save_settings()
        self.logic.connect(mac)

    def on_connection_success(self):
        self.status_indicator.configure(text="● Connected", text_color="green")
        self.unlock_controls()
        self.update_status("Successfully connected.")

    def on_connection_fail(self):
        self.status_indicator.configure(text="● Failed", text_color="red")
        self.lock_controls()

    def update_status(self, msg):
        self.status_bar.configure(text=msg)

    # --- COMMAND TRIGGERS ---

    def toggle_power(self):
        val = 0x01 if self.power_switch.get() else 0x00
        self.logic.send([0x7e, 0x04, 0x04, 0x01, 0x00, val, 0xff, 0x00, 0xef])

    def pick_color(self):
        color = colorchooser.askcolor(title="Choose LED Color")[0]
        if color:
            r, g, b = [int(x) for x in color]
            self.color_btn.configure(fg_color='#%02x%02x%02x' % (r, g, b))
            self.logic.send([0x7e, 0x07, 0x05, 0x03, r, g, b, 0x00, 0xef])

    def update_brightness(self, value):
        self.logic.send([0x7e, 0x04, 0x01, int(value), 0x00, 0x00, 0x00, 0x00, 0xef])

if __name__ == "__main__":
    app = App()
    app.mainloop()