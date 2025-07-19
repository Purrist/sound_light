import numpy as np
from pydub import AudioSegment
import os
import time

def generate_pink_noise(duration_ms=10000):
    """
    Generates a pink noise audio segment.
    
    :param duration_ms: Duration of the noise in milliseconds.
    :return: A pydub AudioSegment object of the generated pink noise.
    """
    # Pink noise generation is complex. For now, we'll start with white noise as a placeholder,
    # which is much simpler to generate. We can upgrade the algorithm later.
    
    # Parameters
    sampling_rate = 44100  # CD quality audio
    num_samples = int(sampling_rate * duration_ms / 1000)
    
    # Generate random samples for white noise
    samples = np.random.normal(0, 1, num_samples).astype(np.float32)
    
    # --- Convert numpy array to pydub AudioSegment ---
    # Ensure samples are in the correct range [-1, 1] for 32-bit float
    samples /= np.max(np.abs(samples))
    
    # Convert to 16-bit integers, which is what pydub expects
    samples_16bit = (samples * 32767).astype(np.int16)
    
    # Create a mono AudioSegment
    noise_segment = AudioSegment(
        samples_16bit.tobytes(),
        frame_rate=sampling_rate,
        sample_width=2,  # 2 bytes = 16 bits
        channels=1       # Mono
    )
    
    return noise_segment

def process_and_save_track(audio_segment, track_type, save_path_func, params):
    """
    Applies effects to an audio segment and saves it as a temporary file.
    
    :param audio_segment: The input pydub AudioSegment.
    :param track_type: 'mainsound' or 'plussound'.
    :param save_path_func: Function to get the save directory (e.g., get_shared_audio_path).
    :param params: A dictionary of processing parameters from the request.
    :return: The temporary filename.
    """
    # Apply volume change
    volume_db = params.get('volume_db', -6.0) # Default to -6dB
    processed_segment = audio_segment + volume_db
    
    # Apply fade in and fade out
    fade_in_ms = params.get('fade_in_ms', 1000)
    fade_out_ms = params.get('fade_out_ms', 1000)
    processed_segment = processed_segment.fade_in(fade_in_ms).fade_out(fade_out_ms)
    
    # Convert to stereo if requested
    if params.get('channels', 1) == 2:
        processed_segment = processed_segment.set_channels(2)
        
    # Generate a unique temporary filename
    timestamp = int(time.time() * 1000)
    temp_filename = f"temp_{track_type}_{timestamp}.wav"
    
    # Define the full save path
    save_path = os.path.join(save_path_func(track_type), temp_filename)
    
    # Export the file
    processed_segment.export(save_path, format="wav")
    
    return temp_filename