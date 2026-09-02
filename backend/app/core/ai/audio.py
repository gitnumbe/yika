"""音频预处理。前端 MediaRecorder 产出 webm/opus，Qwen3-ASR 需要 16kHz 单声道 WAV（决策 09）。

生产级：必须 ffmpeg 转码（-ar 16000 -ac 1）。转码失败抛 AudioTranscodeError，
由流水线降级（标记 transcode_failed，支持重试，绝不静默）。
"""
import shutil
import subprocess


class AudioTranscodeError(Exception):
    """转码失败（音频无效 / ffmpeg 缺失）"""


def prepare_audio(path: str) -> bytes:
    """转码为 16kHz 单声道 WAV 并返回字节流（兼容 16k 采样率输入）。"""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise AudioTranscodeError("ffmpeg not found in PATH")

    # 无论输入什么格式，一律转 16kHz mono PCM WAV
    out = path + ".16k.wav"
    try:
        proc = subprocess.run(
            [ffmpeg, "-y", "-i", path, "-ar", "16000", "-ac", "1", "-f", "wav", out],
            capture_output=True,
            timeout=600,
        )
        if proc.returncode != 0:
            raise AudioTranscodeError(f"ffmpeg failed: {proc.stderr.decode(errors='ignore')[:300]}")
    except subprocess.TimeoutExpired as e:
        raise AudioTranscodeError("ffmpeg timeout") from e

    with open(out, "rb") as f:
        data = f.read()
    return data
