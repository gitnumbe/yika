"""音频预处理。前端 MediaRecorder 产出 webm/opus，FunASR 需要 16kHz 单声道 WAV。

真实联调时，这里需要 ffmpeg 转码。MVP 阶段（mock 测试）直接读文件字节，
转码逻辑留 TODO，待 FunASR 端点就绪 + ffmpeg 可用后补。
"""


def prepare_audio(path: str) -> bytes:
    # TODO(联调): 转码 webm -> 16kHz 单声道 WAV
    #   ffmpeg -i {path} -ar 16000 -ac 1 {path}.wav
    # 然后读 .wav。当前直接读原文件字节（mock 测试用）。
    with open(path, "rb") as f:
        return f.read()
