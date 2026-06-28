import sys
import os

# --- WINDOWS PYTHON-VLC DLL PATCH ---
# Tell Python exactly where to look for libvlc.dll before importing vlc
if sys.platform == "win32":
    vlc_path = r"C:\Program Files\VideoLAN\VLC"
    if os.path.exists(vlc_path):
        os.add_dll_directory(vlc_path)
    else:
        print(f"Warning: VLC directory not found at {vlc_path}. "
              f"Make sure VLC Media Player is installed!")

# Now it is completely safe to import vlc!
import json
import socket
import time
import colorsys
import vlc

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
FEATURES_FILE = "music_features.jsonl"

def load_track_features(title_keyword):
    """Searches the JSONL library for a track matching the title keyword."""
    print(f"Searching library for: '{title_keyword}'...")
    with open(FEATURES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            track = json.loads(line)
            if title_keyword.lower() in track["title"].lower():
                return track
    return None

def play_synced_show(track):
    # 1. Initialize VLC Player Instance
    instance = vlc.Instance()
    player = instance.media_player_new()
    
    # Load the track file path saved during feature extraction
    audio_path = track["file_path"]
    if not os.path.exists(audio_path):
        print(f"Error: Physical audio file not found at: {audio_path}")
        return
        
    media = instance.media_new(audio_path)
    player.set_media(media)

    # 2. Set up network socket to communicate with the BLE daemon
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    hues = track["light_hue"]
    sats = track["light_saturation"]
    brights = track["light_brightness"]
    fps = track["fps"]
    total_frames = len(hues)

    print(f"\nLoaded Match: {track['title']} by {track['artist']}")
    print(f"Total Light Frames: {total_frames} | Pre-analyzed FPS: {fps}")
    print("------------------------------------------------------------")
    print("Commands: Press Ctrl+C in this terminal to stop everything safely.")
    input("Press ENTER to start the media playback and synchronized light show...")

    player.play()
    
    # --- FIX: Wait for VLC to transition into a valid active state ---
    print("Initializing media streams...")
    startup_timeout = time.time() + 3.0  # 3-second safety cutoff
    
    while player.get_state() not in [vlc.State.Playing, vlc.State.Buffering]:
        if player.get_state() == vlc.State.Error:
            print("Error: LibVLC failed to load or decode the file.")
            return
        if time.time() > startup_timeout:
            print("Error: VLC playback initialization timed out.")
            return
        time.sleep(0.01)

    # Brief baseline buffer settle sleep
    time.sleep(0.2)
    
    print("Playback active! Light show synchronized.")
    last_sent_frame = -1

    try:
        # Loop continues while VLC is actively playing or paused
        while player.get_state() in [vlc.State.Playing, vlc.State.Paused]:
            
            # Get current time position directly from VLC engine (in milliseconds)
            vlc_time_ms = player.get_time()
            
            if vlc_time_ms < 0:
                # Handshake initializing, skip frame lookup loop cycle
                time.sleep(0.01)
                continue
                
            # Convert millisecond clock position to our exact telemetry frame index
            current_seconds = vlc_time_ms / 1000.0
            target_frame = int(current_seconds * fps)
            
            # Constrain frame boundary index bounds safely
            target_frame = max(0, min(target_frame, total_frames - 1))
            
            # Only calculate and send data if VLC moved forward to a new frame
            if target_frame != last_sent_frame:
                h = hues[target_frame]
                s = sats[target_frame]
                v = brights[target_frame]
                
                # If player is paused, force lights to drop into a dim frozen state
                if player.get_state() == vlc.State.Paused:
                    v *= 0.3 
                
                # Convert HSV (0-1) to RGB (0-1)
                r_f, g_f, b_f = colorsys.hsv_to_rgb(h, s, v)
                
                # Map floats to Bledom compatible raw integers
                r = int(r_f * 255)
                g = int(g_f * 255)
                b = int(b_f * 255)
                
                # Command 05 frame formatting packet construction
                payload = bytearray([0x7e, 0x07, 0x05, 0x03, r, g, b, 0x00, 0xef])
                sock.sendto(payload, (UDP_IP, UDP_PORT))

                print(f"Playing Frame: {target_frame:04d} | Time: {vlc_time_ms/1000.0:06.2f}s | Target RGB: ({r:3d}, {g:3d}, {b:3d})    ", end="\r")
                
                last_sent_frame = target_frame
            
            # High-frequency poll rate (approx 100hz) to guarantee zero visual latency
            time.sleep(0.01)
            
        print("\nPlayback complete. Ending light show.")

    except KeyboardInterrupt:
        print("\nStopping audio playback and light show...")
        player.stop()
    finally:
        # Turn the lights completely off safely (Command 04 Off)
        off_cmd = bytearray([0x7e, 0x04, 0x04, 0x01, 0x00, 0x00, 0xff, 0x00, 0xef])
        sock.sendto(off_cmd, (UDP_IP, UDP_PORT))
        sock.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python middleman_vlc_player.py '<track_title_keyword>'")
        sys.exit(1)
        
    search_term = sys.argv[1]
    track_data = load_track_features(search_term)
    
    if track_data:
        play_synced_show(track_data)
    else:
        print(f"Error: Could not find any track matching '{search_term}' in library.")