# api/generator.py (最终修复版 4.3)

import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, lfilter
import os
import time
from datetime import datetime

def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = lfilter(b, a, data)
    return y

def generate_noise(duration_s=10, color='pink', channels=2, tone_cutoff_hz=8000, resonance=1.0, stereo_width=0.8):
    """
    Generates high-quality, SEAMLESSLY LOOPABLE noise.
    """
    sampling_rate = 44100
    num_samples = int(sampling_rate * duration_s)

    # --- KEY CHANGE FOR SEAMLESS LOOPING ---
    # We generate noise in the frequency domain, which is inherently periodic
    # when transformed back to the time domain. This ensures the last sample
    # perfectly wraps around to the first sample.

    # 1. Generate random phase and amplitude in the frequency domain
    fft_shape = (num_samples // 2 + 1, channels)
    # Amplitude is random, phase is random
    fft_amplitude = np.random.uniform(0, 1, fft_shape)
    fft_phase = np.random.uniform(0, 2 * np.pi, fft_shape)
    fft_white = fft_amplitude * np.exp(1j * fft_phase)
    
    # 2. Create the pink noise filter
    frequencies = np.fft.rfftfreq(num_samples, 1 / sampling_rate)
    frequencies[0] = 1e-6  # Avoid division by zero
    pink_filter = 1 / np.sqrt(frequencies)
    
    # 3. Apply the filter in the frequency domain
    fft_pink = fft_white * pink_filter[:, np.newaxis]
    
    # 4. Transform back to the time domain. The result is seamlessly loopable.
    noise_stereo = np.fft.irfft(fft_pink, n=num_samples, axis=0)
    # --- END OF KEY CHANGE ---
        
    # Apply low-pass filter for tone control (remains the same)
    if tone_cutoff_hz < (sampling_rate / 2 - 1):
        for i in range(channels):
            noise_stereo[:, i] = butter_lowpass_filter(noise_stereo[:, i], tone_cutoff_hz, sampling_rate)

    # Apply stereo width (remains the same)
    mono_signal = np.mean(noise_stereo, axis=1)
    for i in range(channels):
        noise_stereo[:, i] = stereo_width * noise_stereo[:, i] + (1 - stereo_width) * mono_signal
    
    # Normalize and convert to 16-bit (remains the same)
    noise_stereo /= np.max(np.abs(noise_stereo)) * 1.05
    samples_16bit = (noise_stereo * 32767).astype(np.int16)
    
    noise_segment = AudioSegment(
        samples_16bit.tobytes(),
        frame_rate=sampling_rate,
        sample_width=2,
        channels=channels
    )

    return noise_segment

# --- KEY CHANGE: This function now accepts a string path ---
def process_and_save_track(audio_segment, track_type, save_directory_path):
    """Saves the track as a temporary file to the specified directory path."""
    timestamp = datetime.now().strftime("%H%M%S")
    temp_filename = f"temp_{timestamp}.wav"
    
    # save_directory_path is now a string like '/path/to/instance/audio/mainsound'
    full_save_path = os.path.join(save_directory_path, temp_filename)
    
    audio_segment.export(full_save_path, format="wav")
    
    return temp_filename