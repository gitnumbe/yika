"""录音后处理流水线编排：转写 → 去噪 → 笔记整理 → 落 Note。

这是录音链路的编排层，按顺序调用 asr/denoise/note_gen，逐步更新 Recording 状态。
需求提炼（req_extract）不在流水线里自动跑，而是由用户在笔记上手动触发（防幻觉铁律）。
"""
from ..models import Note, Recording
from . import asr, audio, denoise, note_gen


def process_recording(db, recording_id: int) -> None:
    rec = db.get(Recording, recording_id)
    if not rec:
        return

    # 1. 转写
    rec.status = "transcribing"
    db.commit()
    raw_audio = audio.prepare_audio(rec.audio_path)
    text = asr.get_asr().transcribe(raw_audio)
    rec.transcript = text

    # 2. 去噪
    rec.status = "denoising"
    db.commit()
    clean = denoise.denoise_transcript(text)
    rec.transcript = clean

    # 3. 笔记整理
    rec.status = "noting"
    db.commit()
    note_data = note_gen.generate_note(clean)
    note = Note(
        project_id=rec.project_id,
        scene=rec.scene,
        transcript=clean,
        author_id=rec.author_id,
        **note_data,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    # 4. 完成
    rec.status = "done"
    db.commit()
