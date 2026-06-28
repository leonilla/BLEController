# LED Audio Sync System: Feature Extraction & Reactive Math Guide

This project transforms arbitrary audio files into high-fidelity, real-time light shows streamed over UDP to a Bluetooth Low Energy (BLE) LED strip. Instead of relying on a lagging real-time microphone stream, this system uses **pre-analysis**, extracting structural features from an audio file ahead of time to map out a precise lighting telemetry profile.

---

## 📊 1. How Audio Features Are Extracted

During the pre-analysis stage, your extraction script runs the audio file through `librosa` (a python signal processing library) and slices the song into discrete time windows called **frames** (matching your target FPS, usually ~43 frames per second). 

For every single split-second frame, three distinct musical elements are extracted and tracked:

### A. Root-Mean-Square (RMS) Energy $\rightarrow$ Baseline Amplitude
RMS calculates the average power of the audio signal in a given window. 
* **The Concept:** Think of this as the continuous volume or "loudness" curve of the track.
* **The Light Mapping:** It forms the foundation for baseline LED brightness, scaling how much the ambient lighting glows during choruses versus quiet verses.

### B. Spectral Flux / Onset Strength $\rightarrow$ Percussive Transients
Instead of just listening to volume, the script measures the *rate of change* in the audio spectrum from one millisecond to the next.
* **The Concept:** When a drum stick hits a snare drum or a heavy electronic kick drops, there is a massive, instantaneous spike in frequency energy. This is an **onset transient**.
* **The Light Mapping:** These spikes are isolated and layered on top of the RMS energy. This is what allows your LED strip to distinctively "flash" precisely on drum beats, even if the song is already loudly roaring in the background.

### C. 12-Bin Chromagram $\rightarrow$ Harmonic Content
Human music is built on 12 distinct pitch classes ($C, C\sharp, D, \dots, B$). A Chromagram filters out the octave/bass information and measures how much of each of those 12 notes is present in a frame.
* **The Concept:** If a keyboard plays a clean C-Major chord, the bins for $C$, $E$, and $G$ will spike. If the song shifts to a G-Minor chord, the energy shifts to an entirely different set of bins.
* **The Light Mapping:** These 12 values are mapped across a $360^\circ$ circular Hue wheel ($0.0 \dots 1.0$), determining the exact baseline color of the LEDs based on the active musical harmonies.

---

## ⚡ 2. The Advanced Mathematics of Visual Reactivity

A naive, linear mapping of audio energy directly to LEDs feels muddy, visually dull, and flat. Your pipeline implements a couple of aggressive power-scaling algorithms to bridge the gap between digital signals and human perception:

### Fix 1: The Contrast Boost (Gamma Correction)
Human eyes perceive light intensity exponentially, not linearly. If an LED drops from 100% to 50% brightness, your brain barely registers a difference. 
To make the light show pop, the middleman applies **Gamma Correction** by raising the raw normalized dynamics curve to an aggressive power ($2.2$):

$$V_{\text{out}} = V_{\text{in}}^{2.2}$$

* **Why it works:** If a quiet part of a song has an intensity value of `0.3` (30%), a linear system keeps it quite bright. Your system calculates $0.3^{2.2} \approx 0.06$ (6%). This forces the baseline quiet moments into deep, dark shadows, creating an extreme visual runway for when a drum hit drops and spikes the lights back to a piercing 100% (`1.0`).

### Fix 2: Eradicating "Muddy Colors" (Chroma Peak-Stretching)
When an entire band plays, minor background notes and guitar distortion bleed into the Chromagram. An average calculation results in a messy "brown noise" color blend where the LED strip constantly hovers around an uninspiring middle-ground yellow or orange.

To fix this, your extraction loop subjects the 12 note bins to a high-power exponent array ($4.0$):

$$\text{Stretched Note} = \text{Normalized Note}^{4.0}$$

* **Why it works:** Imagine a frame where a dominant note is at `0.9` and a trailing resonance note is at `0.4`. 
  * *Linear:* The dominant note is only $2.25\times$ stronger than the background noise.
  * *Power-Stretched:* $0.9^4 = 0.65$, while $0.4^4 = 0.025$. Now, the dominant frequency is **$26\times$ stronger** than the background noise. 
* This mathematical filter smashes background harmonies out of the calculation, allowing the single strongest chord tone of that exact millisecond to take the wheel—yielding vivid, saturated, and highly distinct color shifts on every single chord change.

---

## ⏱️ 3. Real-Time Tracking & Timeline Interpolation

The core loop inside `lightshow_middleman_2.py` monitors your desktop VLC application over a local TCP network socket. 

Because VLC's Remote Control engine only reports playback progress in whole, integer seconds (`1s`, `2s`, `3s`), a standard telemetry lookup would lock up and only change colors once per second—missing your 43 frame-per-second targets entirely.

Your middleman resolves this using a **Hybrid Local Interpolation Engine**:
1. Every time the middleman loop ticks, it queries VLC's playback state.
2. The instant VLC reports that the integer second has ticked forward (e.g., from `1` to `2`), the middleman anchors that moment to your computer's high-resolution internal hardware clock (`time.perf_counter()`).
3. On sub-millisecond iterations where VLC is still stubbornly reporting `2s`, your code calculates exactly how much local time has passed since that anchor point was established:

$$\Delta t = \text{time.perf_counter()} - \text{Anchor Time}$$

$$\text{Interpolated Time} = \text{VLC Seconds} + \min(0.99, \Delta t)$$

4. This creates a beautifully fluid timeline array (`2.01s`, `2.02s`, `2.03s`...) that matches your audio speakers flawlessly. The system uses this micro-timestamp to lookup the exact matching row index inside your pre-analyzed `.jsonl` library, flooding your BLE background daemon with zero-latency lighting telemetry!