import asyncio
import threading
import json
import os
import customtkinter as ctk
from tkinter import colorchooser
from bleak import BleakClient

# --- CONFIGURATION ---
CONFIG_FILE = "config.json"
WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

class DisconnectDialog(ctk.CTkToplevel):
    """Custom confirmation dialog for a modern look."""
    def __init__(self, parent, mac, on_confirm):
        super().__init__(parent)
        self.title("Confirm Disconnect")
        self.geometry("300x150")
        self.on_confirm = on_confirm
        
        self.label = ctk.CTkLabel(self, text=f"Close connection with:\n{mac}?", pady=20)
        self.label.pack()

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20)

        self.confirm_btn = ctk.CTkButton(self.btn_frame, text="Confirm", fg_color="#d32f2f", hover_color="#b71c1c", width=100, command=self.do_confirm)
        self.confirm_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(self.btn_frame, text="Cancel", width=100, command=self.destroy)
        self.cancel_btn.pack(side="right", padx=10)

        self.grab_set() # Focus on this window

    def do_confirm(self):
        self.on_confirm()
        self.destroy()

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
            self.app.update_status(f"Error: {e}")
            self.app.on_connection_fail()

    async def _disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.app.on_disconnect_complete()

    async def _send(self, payload):
        if self.client and self.client.is_connected:
            try:
                await self.client.write_gatt_char(self.write_char, bytes(payload))
                self.app.update_status(f"Sent: {bytes(payload).hex(' ')}")
            except Exception as e:
                self.app.update_status(f"Send Error: {e}")

    def connect(self, address):
        asyncio.run_coroutine_threadsafe(self._connect(address), self.loop)

    def disconnect(self):
        asyncio.run_coroutine_threadsafe(self._disconnect(), self.loop)

    def send(self, payload):
        asyncio.run_coroutine_threadsafe(self._send(payload), self.loop)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ELK-BLEDOM Controller")
        
        self.logic = LEDLogic(self)
        self.connected = False
        
        self.setup_ui()
        self.load_settings()
        self.resizable(False, False)
        self.update_idletasks()
        self.geometry("400x550")
        

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # --- PANEL 1: CONFIGURATION (Bordered) ---
        self.config_frame = ctk.CTkFrame(self, border_width=2, border_color="gray30")
        self.config_frame.pack(padx=20, pady=(20, 10), fill="x")
        
        ctk.CTkLabel(self.config_frame, text="CONNECTION SETTINGS", font=("Arial", 11, "bold")).pack(pady=10)
        self.mac_entry = ctk.CTkEntry(self.config_frame, placeholder_text="XX:XX:XX:XX:XX:XX", width=250)
        self.mac_entry.pack(pady=5, padx=20)

        self.launch_check = ctk.CTkCheckBox(self.config_frame, text="Connect on launch")
        self.launch_check.pack(pady=5)

        self.conn_btn = ctk.CTkButton(self.config_frame, text="Connect", command=self.handle_connection_click)
        self.conn_btn.pack(pady=15)

        self.status_indicator = ctk.CTkLabel(self.config_frame, text="● Disconnected", text_color="#ff4444")
        self.status_indicator.pack(pady=(0, 10))

        # --- PANEL 2: CONTROLS (Bordered) ---
        self.ctrl_frame = ctk.CTkFrame(self, border_width=2, border_color="gray30")
        self.ctrl_frame.pack(padx=20, pady=10, fill="x") # Using pack instead of grid
        ctk.CTkLabel(self.ctrl_frame, text="DEVICE CONTROLS", font=("Arial", 11, "bold")).pack(pady=10)
        
        
        # Power Switch
        self.power_switch = ctk.CTkSwitch(self.ctrl_frame, text="Power", command=self.toggle_power)
        self.power_switch.select()
        self.power_switch.pack(pady=10)

        # Color Picker Button
        self.color_btn = ctk.CTkButton(self.ctrl_frame, text="Select Color", fg_color="#333333", command=self.pick_color)
        self.color_btn.pack(pady=15, padx=40)

        # Brightness Slider
        ctk.CTkLabel(self.ctrl_frame, text="Brightness").pack()
        self.bright_slider = ctk.CTkSlider(self.ctrl_frame, from_=0, to=100, command=self.update_brightness)
        self.bright_slider.set(100)
        self.bright_slider.pack(pady=(0, 20))

        # Status Bar
        self.status_bar = ctk.CTkLabel(self, text="  Ready", anchor="w", fg_color="#1a1a1a", height=25)
        self.status_bar.pack(side="bottom", fill="x", pady=(10, 0))

        self.lock_controls()

    def handle_connection_click(self):
        if not self.connected:
            mac = self.mac_entry.get()
            if mac:
                self.update_status("Connecting...")
                self.save_settings()
                self.logic.connect(mac)
        else:
            DisconnectDialog(self, self.mac_entry.get(), self.logic.disconnect)

    def on_connection_success(self):
        self.connected = True
        self.status_indicator.configure(text="● Connected", text_color="#44ff44")
        self.conn_btn.configure(text="Disconnect", fg_color="#d32f2f", hover_color="#b71c1c")
        self.unlock_controls()
        self.update_status("Connected successfully.")

    def on_disconnect_complete(self):
        self.connected = False
        self.status_indicator.configure(text="● Disconnected", text_color="#ff4444")
        self.conn_btn.configure(text="Connect", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#367E96", "#144870"])
        self.lock_controls()
        self.update_status("Disconnected.")

    def on_connection_fail(self):
        self.status_indicator.configure(text="● Failed", text_color="#ff4444")
        self.lock_controls()

    def lock_controls(self):
        for child in self.ctrl_frame.winfo_children():
            if isinstance(child, (ctk.CTkButton, ctk.CTkSlider, ctk.CTkSwitch)):
                child.configure(state="disabled")

    def unlock_controls(self):
        for child in self.ctrl_frame.winfo_children():
            if isinstance(child, (ctk.CTkButton, ctk.CTkSlider, ctk.CTkSwitch)):
                child.configure(state="normal")

    def update_status(self, msg):
        self.status_bar.configure(text=f"  {msg}")

    # --- UPDATED 9-BYTE COMMANDS ---
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

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.mac_entry.insert(0, data.get("mac", ""))
                    if data.get("auto", False):
                        self.launch_check.select()
                        self.after(500, self.handle_connection_click)
            except: pass

    def save_settings(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump({"mac": self.mac_entry.get(), "auto": self.launch_check.get()}, f)

if __name__ == "__main__":
    app = App()
    app.mainloop()