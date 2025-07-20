# api/generator.py (版本 5.0 - 专业助眠版)

import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, lfilter
import os
import time
from datetime import datetime

def butter_bandpass_filter(data, lowcut, highcut, fs, order=2):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    y = lfilter(b, a, data)
    return y

def generate_noise(duration_s=480, # 默认生成 8 分钟
                   low_shelf_gain_db=0,
                   mid_shelf_gain_db=0,
                   high_shelf_gain_db=-6,
                   modulation_rate_hz=0.05, # 极慢的调制，20秒一个周期
                   modulation_depth_db=1.5):
    
    sampling_rate = 44100
    num_samples = int(sampling_rate * duration_s)
    channels = 2

    # 1. Generate seamlessly loopable pink noise in frequency domain
    fft_shape = (num_samples // 2 + 1, channels)
    fft_amplitude = np.random.uniform(0, 1, fft_shape)
    fft_phase = np.random.uniform(0, 2 * np.pi, fft_shape)
    fft_white = fft_amplitude * np.exp(1j * fft_phase)
    frequencies = np.fft.rfftfreq(num_samples, 1 / sampling_rate)
    frequencies[0] = 1e-6
    pink_filter = 1 / np.sqrt(frequencies)
    fft_pink = fft_white * pink_filter[:, np.newaxis]
    noise_stereo = np.fft.irfft(fft_pink, n=num_samples, axis=0)
    noise_stereo /= np.max(np.abs(noise_stereo)) # Normalize

    # 2. Apply 3-band EQ for tonal shaping
    low_freq = butter_bandpass_filter(noise_stereo, 20, 250, sampling_rate)
    mid_freq = butter_bandpass_filter(noise_stereo, 250, 4000, sampling_rate)
    high_freq = butter_bandpass_filter(noise_stereo, 4000, 16000, sampling_rate)

    low_gain = 10**(low_shelf_gain_db / 20)
    mid_gain = 10**(mid_shelf_gain_db / 20)
    high_gain = 10**(high_shelf_gain_db / 20)

    shaped_noise = (low_freq * low_gain) + (mid_freq * mid_gain) + (high_freq * high_gain)
    shaped_noise /= np.max(np.abs(shaped_noise)) # Re-normalize

    # 3. Apply very slow, subtle modulation (LFO) for "breathing" effect
    t = np.linspace(0., duration_s, num_samples, endpoint=False)
    # Sine wave for modulation, ensuring it loops perfectly
    mod_wave = (np.sin(2 * np.pi * modulation_rate_hz * t) + 1) / 2 # Range 0 to 1
    mod_depth_gain = 10**(modulation_depth_db / 20)
    
    # Apply modulation: gain ranges from 1.0 down to (1/mod_depth_gain)
    modulation_gain = 1 - (mod_wave * (1 - (1/mod_depth_gain)))
    
    final_noise = shaped_noise * modulation_gain[:, np.newaxis]
    final_noise /= np.max(np.abs(final_noise)) * 1.05
    
    # Convert to 16-bit and create pydub segment
    samples_16bit = (final_noise * 32767).astype(np.int16)
    noise_segment = AudioSegment(
        samples_16bit.tobytes(),
        frame_rate=sampling_rate,
        sample_width=2,
        channels=channels
    )
    return noise_segment

def process_and_save_track(audio_segment, track_type, save_directory_path):
    timestamp = datetime.now().strftime("%H%M%S")
    temp_filename = f"temp_{timestamp}.wav"
    full_save_path = os.path.join(save_directory_path, temp_filename)
    audio_segment.export(full_save_path, format="wav")
    return temp_filename