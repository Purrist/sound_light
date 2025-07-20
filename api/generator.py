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
    sampling_rate = 44100
    num_samples = int(sampling_rate * duration_s)
    fft_shape = (num_samples // 2 + 1, channels)
    fft_white = (np.random.randn(*fft_shape) + 1j * np.random.randn(*fft_shape)).astype(np.complex64)
    frequencies = np.fft.rfftfreq(num_samples, 1/sampling_rate)
    frequencies[0] = 1e-6
    pink_filter = 1 / np.sqrt(frequencies)
    fft_pink = fft_white * pink_filter[:, np.newaxis]
    noise_stereo = np.fft.irfft(fft_pink, n=num_samples, axis=0)
    
    if tone_cutoff_hz < (sampling_rate / 2 - 1):
        for i in range(channels):
            noise_stereo[:, i] = butter_lowpass_filter(noise_stereo[:, i], tone_cutoff_hz, sampling_rate)

    mono_signal = np.mean(noise_stereo, axis=1)
    for i in range(channels):
        noise_stereo[:, i] = stereo_width * noise_stereo[:, i] + (1 - stereo_width) * mono_signal
    
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