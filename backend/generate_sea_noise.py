import numpy as np
from scipy.io.wavfile import write
import os

def generate_pink_noise_wav(
    output_path="static/mainsound/sea.wav",
    duration=60,
    sample_rate=44100
):
    """
    生成粉红噪声并保存为 WAV 文件（模拟海洋声音）
    """
    print(f"生成中：{output_path}")
    n_samples = duration * sample_rate
    uneven = n_samples % 2
    X = np.random.randn(n_samples // 2 + 1 + uneven) + 1j * np.random.randn(n_samples // 2 + 1 + uneven)
    S = np.sqrt(np.arange(len(X)) + 1.)
    y = (np.fft.irfft(X / S)).real

    # 归一化到 16-bit PCM 格式
    y = y / np.max(np.abs(y))
    y = (y * 32767).astype(np.int16)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 写入 WAV 文件
    write(output_path, sample_rate, y)
    print(f"✅ 已生成粉红噪声：{output_path}，时长 {duration} 秒")

if __name__ == '__main__':
    generate_pink_noise_wav()
