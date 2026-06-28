import argparse
import os
import json
import librosa
import numpy as np

def parse_arguments():
    """Builds and compiles explicit command line arguments for batch asset extraction."""
    parser = argparse.ArgumentParser(
        description="Fidelity music features audio pre-analyzer script."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to the input text file containing absolute paths to analyze."
    )
    parser.add_argument(
        "output",
        type=str,
        help="Target destination filename for the exported JSONL structural matrix database."
    )
    return parser.parse_args()

def parse_directory_metadata(file_path):
    """
    Assumes a (/Artist/Album/Track) dir+subdir structure
    to extract artist and album info from file path.
    """
    normalized = os.path.normpath(file_path)
    parts = normalized.split(os.sep)
    if len(parts) >= 3:
        artist = parts[-3].split(" - ")[0]
        album = parts[-2].split(" - ")[0]
        return artist, album
    return "Unknown Artist", "Unknown Album"

def extract_track_features(file_path):
    try:
        # Load audio at standard analysis sample rate
        y, sr = librosa.load(file_path, sr=22050, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)
        
        # --- 1. EXTRACT CORE TIME-SERIES DATA ---
        rms = librosa.feature.rms(y=y)[0]
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        
        # Capture the frame rate so the playback script knows exactly how fast to step
        hop_length = 512
        fps = sr / hop_length
        
        # --- 2. PER-TRACK DYNAMIC NORMALIZATION ---
        # Prevent division by zero with a tiny epsilon (1e-6)
        rms_norm = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)
        onset_norm = (onset_env - np.min(onset_env)) / (np.max(onset_env) - np.min(onset_env) + 1e-6)
        centroid_norm = (centroid - np.min(centroid)) / (np.max(centroid) - np.min(centroid) + 1e-6)
        
        # --- 3. DYNAMICS GENERATION (Value / Brightness) ---
        # Push more weight into the punchy onset transients
        brightness_curve = (rms_norm * 0.4) + (onset_norm * 0.6)
        
        # Apply Gamma Correction (raising to power of 2.0 or 2.5 expands contrast)
        brightness_curve = np.power(brightness_curve, 2.2)
        brightness_curve = np.clip(brightness_curve, 0.0, 1.0)
        
        # Fast attack, but slightly faster decay so it doesn't stay "bloated" with light
        for i in range(1, len(brightness_curve)):
            if brightness_curve[i] < brightness_curve[i-1]:
                # 0.5 decay coefficient makes the flashes much snappier and dynamic
                brightness_curve[i] = (brightness_curve[i-1] * 0.5) + (brightness_curve[i] * 0.5)

        # --- 4. COLOR HUE GENERATION (Stretched Harmonic Dominance) ---
        note_hues = np.linspace(0.0, 1.0, 12, endpoint=False)
        hue_curve = []
        
        for frame in chroma.T:
            if frame.sum() > 0:
                # Normalize frame vector to 0-1
                frame_norm = frame / (np.max(frame) + 1e-6)
                
                # Exaggerate differences: Raise notes to a high power (e.g., 4.0)
                # This makes the dominant note smash everything else out of the way!
                stretched_frame = np.power(frame_norm, 4.0)
                
                # Calculate the hue based only on the exaggerated dominant frequencies
                weighted_hue = np.sum(stretched_frame * note_hues) / (stretched_frame.sum() + 1e-6)
                hue_curve.append(float(weighted_hue))
            else:
                hue_curve.append(0.0)
                
        # Lower the smoothing windows slightly (from 9 frames down to 5) 
        # so the colors react quickly to chord changes instead of blending together.
        hue_curve = np.convolve(hue_curve, np.ones(5)/5, mode='same')

        # --- 5. SATURATION GENERATION (Timbral "Bleaching") ---
        # Invert the normalized centroid: high treble / hiss pushes saturation down toward white
        saturation_curve = 1.0 - (centroid_norm * 0.7)
        saturation_curve = np.clip(saturation_curve, 0.0, 1.0)
        
        # Extract artist and album metadata from path
        artist_meta, album_meta = parse_directory_metadata(file_path)
        
        # --- 6. BUILD SYSTEM OUTPUT ---
        track_data = {
            "file_path": os.path.abspath(file_path),
            "title": os.path.splitext(os.path.basename(file_path))[0],
            "artist": artist_meta, 
            "album": album_meta,
            "duration": round(duration, 1),
            "fps": round(fps, 2),
            # Full fidelity lighting telemetry arrays
            "light_hue": [round(float(h), 3) for h in hue_curve],
            "light_saturation": [round(float(s), 3) for s in saturation_curve],
            "light_brightness": [round(float(b), 3) for b in brightness_curve],
        }
        return track_data
        
    except Exception as e:
        print(f"Skipping {file_path} due to error: {e}")
        return None

def compute_and_save_library(txt_file_path, output_jsonl):
    if not os.path.exists(txt_file_path):
        print(f"Error: The file list path '{txt_file_path}' does not exist.")
        return

    print(f"Reading file paths from: {txt_file_path}...")
    
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        file_paths = [line.strip() for line in f if line.strip()]

    processed_count = 0
    
    with open(output_jsonl, 'w', encoding='utf-8') as f_out:
        for full_path in file_paths:
            if os.path.exists(full_path) and full_path.lower().endswith(('.mp3', '.wav', '.flac')):
                print(f"Analyzing: {os.path.basename(full_path)}")
                res = extract_track_features(full_path)
                if res:
                    f_out.write(json.dumps(res) + '\n')
                    f_out.flush()
                    processed_count += 1
            elif not os.path.exists(full_path):
                print(f"File not found, skipping: {full_path}")
                    
    if processed_count == 0:
        print("No audio tracks successfully processed.")
        return
            
    print(f"Features for {processed_count} tracks extracted to {output_jsonl}")

if __name__ == "__main__":
    args = parse_arguments()
    compute_and_save_library(args.input, args.output)