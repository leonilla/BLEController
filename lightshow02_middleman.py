import sys
import os
import argparse

# --- WINDOWS PYTHON-VLC DLL PATCH ---
if sys.platform == "win32":
    vlc_path = r"C:\Program Files\VideoLAN\VLC"
    if os.path.exists(vlc_path):
        os.add_dll_directory(vlc_path)
    else:
        print(f"Warning: VLC directory not found at {vlc_path}. "
              f"Make sure VLC Media Player is installed!")

import json
import socket
import time
import colorsys
import re
import urllib.parse
import vlc

def parse_arguments():
    """Parses command line arguments to accept a custom configuration path."""
    parser = argparse.ArgumentParser(
        description="Real-time VLC MIDI-less telemetry lighting sync middleman daemon."
    )
    parser.add_argument(
        "--config", 
        type=str, 
        default="middleman_config.json", 
        help="Path to the system configuration JSON file (default: config.json)"
    )
    return parser.parse_args()

def load_system_config(config_path):
    """Loads runtime environment fields from the designated configuration file."""
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at '{config_path}'")
        print("Please ensure a valid config.json exists or pass one using --config.")
        sys.exit(1)
        
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            return config_data
    except Exception as e:
        print(f"Error reading configuration file: {e}")
        sys.exit(1)

def send_vlc_command(sock, command):
    """Sends a text command to VLC's TCP interface and reads the response."""
    try:
        sock.sendall(f"{command}\n".encode('utf-8'))
        time.sleep(0.04)  # Give VLC a tiny window to respond
        data = sock.recv(4096).decode('utf-8', errors='ignore')
        return data
    except Exception:
        return ""

def get_current_vlc_track_and_state(sock):
    """Queries VLC for the current playing file path, explicit time, and play/pause state."""
    status_data = send_vlc_command(sock, "status")
    
    # 1. Parse playback state (playing vs paused)
    is_paused = "state paused" in status_data.lower()

    # 2. Extract the absolute path from the status update's input segment
    input_match = re.search(r"new input:\s*(.*?)\s*\)\s*$", status_data, re.MULTILINE | re.IGNORECASE)
    
    absolute_windows_path = ""
    if input_match:
        raw_url = input_match.group(1).strip()
        # Clean up URL encodes (like %20) back into real human-readable spaces
        decoded_path = urllib.parse.unquote(raw_url)
        
        # Strip local file URI prefixing schemes if applied by VLC
        if decoded_path.startswith("file:///"):
            decoded_path = decoded_path.replace("file:///", "", 1)
            
        # Standardize all forward/backward slashes to local OS layout
        absolute_windows_path = os.path.normpath(decoded_path)
    
    # 3. Explicitly pull the ticking runtime counter from the media timeline
    time_data = send_vlc_command(sock, "get_time")
    clean_time_str = time_data.replace(">", "").strip()
    
    vlc_seconds = 0.0
    try:
        if clean_time_str.isdigit():
            vlc_seconds = float(clean_time_str)
    except ValueError:
        pass
    
    return absolute_windows_path, vlc_seconds, is_paused

def load_track_by_exact_path(vlc_file_path, features_file):
    """Matches the exact absolute Windows path from VLC directly against the library file paths."""
    if not vlc_file_path:
        return None
        
    target_path_lower = os.path.abspath(vlc_file_path).lower()
    
    with open(features_file, 'r', encoding='utf-8') as f:
        for line in f:
            track = json.loads(line)
            # Strict string equivalence match on full system directories
            if os.path.abspath(track["file_path"]).lower() == target_path_lower:
                return track
                
    return None

def main():
    # Complete arguments and config ingestion pipelines
    args = parse_arguments()
    config = load_system_config(args.config)

    # Dynamic parameter mappings mapped directly from the JSON configurations
    UDP_IP = config.get("UDP_IP", "127.0.0.1")
    UDP_PORT = config.get("UDP_PORT", 5005)
    VLC_TCP_IP = config.get("VLC_TCP_IP", "127.0.0.1")
    VLC_TCP_PORT = config.get("VLC_TCP_PORT", 4212)
    FEATURES_FILE = config.get("FEATURES_FILE", "music_features.jsonl")

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    vlc_sock = None

    print(f"Connecting to your Desktop VLC App on {VLC_TCP_IP}:{VLC_TCP_PORT}...")
    while not vlc_sock:
        try:
            vlc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            vlc_sock.settimeout(2.0) 
            vlc_sock.connect((VLC_TCP_IP, VLC_TCP_PORT))
            
            vlc_sock.sendall(b"\n")
            try:
                vlc_sock.recv(1024)
            except socket.timeout:
                pass
                
            print("Connected to VLC Player successfully!")
        except (ConnectionRefusedError, socket.timeout):
            print("Waiting for you to open VLC Media Player... (Retrying in 2s)")
            if vlc_sock:
                vlc_sock.close()
            vlc_sock = None
            time.sleep(2.0)
            
    current_loaded_path = ""
    track_data = None
    last_sent_frame = -1
    
    # High-resolution sub-second timeline tracking variables
    last_vlc_sec = -1.0
    local_sync_time = 0.0

    print("\nSystem running! Double click any track in your VLC window to trigger lights.")
    print("-------------------------------------------------------------------------")

    try:
        while True:
            # Continually poll the live desktop window parameters
            vlc_path, raw_vlc_seconds, is_paused = get_current_vlc_track_and_state(vlc_sock)
            
            # Switch track assets only when a valid new target directory path arrives
            if vlc_path and vlc_path != current_loaded_path:
                print(f"\n[File Path Active]: {vlc_path}")
                loaded_data = load_track_by_exact_path(vlc_path, FEATURES_FILE)
                
                if loaded_data:
                    track_data = loaded_data
                    current_loaded_path = vlc_path
                    last_sent_frame = -1
                    last_vlc_sec = -1.0  # Reset clock sync anchor
                    print(f"-> Successfully loaded light maps from JSONL library.")
                else:
                    print("-> Error: This specific file path has not been pre-analyzed yet.")

            # --- SUB-SECOND INTERPOLATION CLOCK MATH ---
            current_seconds = raw_vlc_seconds
            
            if not is_paused and track_data:
                # If VLC's integer second ticks forward, baseline sync our internal clock
                if raw_vlc_seconds != last_vlc_sec:
                    last_vlc_sec = raw_vlc_seconds
                    local_sync_time = time.perf_counter()
                else:
                    # If it's the same second, add the high-res elapsed local time fraction
                    elapsed_fraction = time.perf_counter() - local_sync_time
                    # Cap the fraction at 0.99s to keep it from drifting into the next second early
                    current_seconds = raw_vlc_seconds + min(0.99, elapsed_fraction)

            # Keep feeding telemetry values based on the persistent track data profile
            if track_data and current_seconds >= 0:
                hues = track_data["light_hue"]
                sats = track_data["light_saturation"]
                brights = track_data["light_brightness"]
                fps = track_data["fps"]
                total_frames = len(hues)

                # Map running clock timeline markers to pre-calculated indices
                target_frame = int(current_seconds * fps)
                target_frame = max(0, min(target_frame, total_frames - 1))

                if target_frame != last_sent_frame:
                    h = hues[target_frame]
                    s = sats[target_frame]
                    v = brights[target_frame]

                    if is_paused:
                        v *= 0.3

                    # Transform array values to 8-bit RGB components
                    r_f, g_f, b_f = colorsys.hsv_to_rgb(h, s, v)
                    r, g, b = int(r_f * 255), int(g_f * 255), int(b_f * 255)

                    # Build protocol payload (Command 05 format)
                    payload = bytearray([0x7e, 0x07, 0x05, 0x03, r, g, b, 0x00, 0xef])
                    udp_sock.sendto(payload, (UDP_IP, UDP_PORT))
                    
                    print(f"Tracking Show: Frame {target_frame:04d} | Time: {current_seconds:06.2f}s | RGB: ({r:3d}, {g:3d}, {b:3d})   ", end="\r")
                    last_sent_frame = target_frame

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nExiting tracker...")
    finally:
        if vlc_sock:
            vlc_sock.close()
        # Blackout safety signal on unexpected exit bounds
        off_cmd = bytearray([0x7e, 0x04, 0x04, 0x01, 0x00, 0x00, 0xff, 0x00, 0xef])
        udp_sock.sendto(off_cmd, (UDP_IP, UDP_PORT))
        udp_sock.close()

if __name__ == "__main__":
    main()