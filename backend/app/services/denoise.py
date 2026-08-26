from .llm import get_denoise_llm

PROMPT = """你是会议记录清洗助手。下面是转写文本。请删除寒暄、重复、口水话、与主题无关的内容，保留有信息量的句子。直接输出清洗后的文本，不要解释。\n\n转写文本：\n{transcript}"""


def denoise_transcript(transcript: str) -> str:
    llm = get_denoise_llm()
    return llm.chat([{"role": "user", "content": PROMPT.format(transcript=transcript)}])
