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
    Generates high-quality, SEAMLESSLY LOOPABLE noise.
    """
    sampling_rate = 44100
    num_samples = int(sampling_rate * duration_s)

    if color == 'pink':
        # Use a method that is inherently tileable (periodic) for looping
        # Generate white noise in the frequency domain
        fft_shape = (num_samples // 2 + 1, channels)
        fft_white = (np.random.randn(*fft_shape) + 1j * np.random.randn(*fft_shape)).astype(np.complex64)
        
        # Create pink filter
        frequencies = np.fft.rfftfreq(num_samples, 1/sampling_rate)
        frequencies[0] = 1e-6 # Avoid division by zero
        pink_filter = 1 / np.sqrt(frequencies)
        
        # Apply filter
        fft_pink = fft_white * pink_filter[:, np.newaxis]
        
        # Transform back to time domain
        noise_stereo = np.fft.irfft(fft_pink, n=num_samples, axis=0)

    else: # Fallback to simpler white noise
        noise_stereo = np.random.uniform(-1, 1, (num_samples, channels)).astype(np.float32)
        
    # Apply low-pass filter for tone control
    if tone_cutoff_hz < (sampling_rate / 2 - 1):
        for i in range(channels):
            noise_stereo[:, i] = butter_lowpass_filter(noise_stereo[:, i], tone_cutoff_hz, sampling_rate)

    # Apply stereo width
    mono_signal = np.mean(noise_stereo, axis=1)
    for i in range(channels):
        noise_stereo[:, i] = stereo_width * noise_stereo[:, i] + (1 - stereo_width) * mono_signal
    
    # Normalize to prevent clipping
    noise_stereo /= np.max(np.abs(noise_stereo)) * 1.05 # Add a little headroom
    
    # Convert to 16-bit integer samples
    samples_16bit = (noise_stereo * 32767).astype(np.int16)
    
    # Create pydub audio segment
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