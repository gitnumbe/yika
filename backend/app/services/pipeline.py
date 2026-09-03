"""录音后处理流水线编排：转写 → 去噪 → 笔记整理 → 落 Note。

生产级（开发文档 §8.6）：
1. 每步失败不静默：抛异常由 tasks.py 重试（attempts+1 / 指数退避 / 3 次后 failed 告警）。
2. 音频转码失败（AudioTranscodeError）→ 上行给任务层标记 transcode_failed。
3. 需求提炼（req_extract）不在流水线里自动跑，而是由用户在笔记上手动触发（防幻觉铁律）。
"""
from ..models import Note, Project, Recording
from . import asr, audio, denoise, note_gen


def process_recording(db, recording_id: int) -> None:
    rec = db.get(Recording, recording_id)
    if not rec:
        return

    # 0. 音频准备（转码失败 → 抛 AudioTranscodeError，由任务层标记重试）
    rec.status = "preparing"
    db.commit()
    raw_audio = audio.prepare_audio(rec.audio_path)

    # 1. 转写（Qwen3-ASR，决策 09）
    rec.status = "transcribing"
    db.commit()
    text = asr.get_asr().transcribe(raw_audio)
    rec.transcript = text

    # 2. 去噪（返回 dict：{text, quality}，失败自动规则兜底）
    rec.status = "denoising"
    db.commit()
    denoise_result = denoise.denoise_transcript(text)
    rec.transcript = denoise_result["text"]

    # 3. 笔记整理（四块结构；LLM 失败返回降级结构，不阻塞）
    rec.status = "noting"
    db.commit()
    note_data = note_gen.generate_note(denoise_result["text"])
    if note_data.get("quality", {}).get("degraded"):
        # 笔记降级也落库，但记录 quality 便于前端提示"AI 降级"
        pass

    # v3：Note 挂在 customer 下（customer_id/group_id），归属从录音所在 project 解析。
    # A6 四块结构化写入 ai_structured（JSON），quality 写入 quality_flags。
    # 录音未关联 project（无法解析客户/组上下文）时跳过落 Note，不阻塞转写完成。
    project = db.get(Project, rec.project_id) if rec.project_id else None
    if project:
        note = Note(
            customer_id=project.customer_id,
            group_id=project.group_id,
            scenario=rec.scene or "req_discussion",
            transcript=denoise_result["text"],
            audio_path=rec.audio_path or "",
            ai_structured={
                "summary": note_data.get("summary", "") or "",
                "points": note_data.get("points", []) or [],
                "decisions": note_data.get("decisions", []) or [],
                "todos": note_data.get("todos", []) or [],
            },
            quality_flags=note_data.get("quality", {}) or {},
            note_author_id=rec.author_id,
        )
        db.add(note)
        db.commit()
        db.refresh(note)

    # 4. 完成
    rec.status = "done"
    db.commit()
