/** TTS 朗读 hook：调 /tts 端点拿 audio_url → <audio> 播放。
    懒合成（后端缓存复用）；失败降级为提示不阻塞。 */
import { useRef, useState } from "react";
import { apiFetch, API_BASE } from "../api/client";

export function useTTS() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);

  async function speak(url: string) {
    if (loading) return;
    setLoading(true);
    try {
      const res = await apiFetch(url, { method: "POST" });
      // audio_url 是服务端相对路径，拼成可播放的绝对 URL
      const abs = res.audio_url.startsWith("http")
        ? res.audio_url
        : `${API_BASE}${res.audio_url}`;
      if (audioRef.current) {
        audioRef.current.src = abs;
        await audioRef.current.play();
        setPlaying(true);
      }
    } catch {
      alert("语音服务暂不可用，已降级为文字展示");
    } finally {
      setLoading(false);
    }
  }

  return { speak, playing, loading };
}
