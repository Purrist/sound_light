import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, lfilter
import os
import time

def butter_lowpass_filter(data, cutoff, fs, order=5):
    """Applies a Butterworth low-pass filter to the data."""
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = lfilter(b, a, data)
    return y

def generate_noise(duration_s=30, color='pink', channels=2, tone_cutoff_hz=8000, stereo_width=0.8):
    """
    Generates high-quality noise with customizable parameters.
    """
    sampling_rate = 44100
    num_samples = int(sampling_rate * duration_s)

    # Generate stereo white noise as the base
    white_noise_stereo = np.random.uniform(-1, 1, (num_samples, 2)).astype(np.float32)

    if color == 'pink':
        fft_white = np.fft.rfft(white_noise_stereo, axis=0)
        frequencies = np.fft.rfftfreq(num_samples, 1/sampling_rate)
        frequencies[0] = 1 
        pink_filter = 1 / np.sqrt(frequencies)
        fft_pink = fft_white * pink_filter[:, np.newaxis]
        pink_noise_stereo = np.fft.irfft(fft_pink, axis=0)
    else:
        pink_noise_stereo = white_noise_stereo
        
    if tone_cutoff_hz < (sampling_rate / 2 - 1): # Ensure cutoff is valid
        pink_noise_stereo[:, 0] = butter_lowpass_filter(pink_noise_stereo[:, 0], tone_cutoff_hz, sampling_rate)
        pink_noise_stereo[:, 1] = butter_lowpass_filter(pink_noise_stereo[:, 1], tone_cutoff_hz, sampling_rate)

    mono_signal = np.mean(pink_noise_stereo, axis=1)
    left_channel = stereo_width * pink_noise_stereo[:, 0] + (1 - stereo_width) * mono_signal
    right_channel = stereo_width * pink_noise_stereo[:, 1] + (1 - stereo_width) * mono_signal
    processed_noise = np.stack([left_channel, right_channel], axis=1)
    
    # Normalize to prevent clipping
    processed_noise /= np.max(np.abs(processed_noise))
    
    samples_16bit = (processed_noise * 32767).astype(np.int16)
    
    noise_segment = AudioSegment(
        samples_16bit.tobytes(),
        frame_rate=sampling_rate,
        sample_width=2,
        channels=channels
    )

    return noise_segment

def process_and_save_track(audio_segment, track_type, save_path_func, params):
    """
    Applies final effects and saves the track as a temporary file.
    """
    volume_db = params.get('volume_db', -6.0)
    fade_in_ms = params.get('fade_in_ms', 1000)
    fade_out_ms = params.get('fade_out_ms', 2000)

    processed_segment = audio_segment + volume_db
    processed_segment = processed_segment.fade_in(fade_in_ms).fade_out(fade_out_ms)
    
    timestamp = int(time.time() * 1000)
    temp_filename = f"temp_{track_type}_{timestamp}.wav"
    save_path = os.path.join(save_path_func(track_type), temp_filename)
    
    processed_segment.export(save_path, format="wav")
    
    return temp_filename