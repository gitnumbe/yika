# 决策 09：语音通道本地自建（STT = Qwen3-ASR-1.7B，TTS = dots.tts-mf）

**状态**：已采纳
**日期**：2026-09-01（v2.0 生产级基线，替代决策 04/03 中 FunASR 的选型）
**变更说明**：v1.0 阶段 STT 用内网 FunASR、无 TTS；v2.0 升级为 STT/TTS 双通道本地自建（数据不出内网 + 生产级质量）。

## 背景

系统新增两项语音能力：

1. **STT（语音转写）**：录音转写是流水线第一环，质量直接影响笔记与需求提炼。
2. **TTS（文本转语音）**：笔记/答疑朗读，给讲师更顺滑的获取方式（v2.0 新增）。

语音数据属于敏感数据（客户沟通内容），**不出内网**是硬约束；同时生产级要求 WER（字错误率）与合成自然度达到可用水平。

## 决策

| 通道 | 选型 | 定位 | 理由 |
| --- | --- | --- | --- |
| **STT** | **Qwen3-ASR-1.7B**（本地部署） | 录音转写 | 国产开源 ASR SOTA：52 语言+22 中文口音识别、20 分钟长音频单次处理、流式/离线一体、强噪环境稳定；1.7B 在开源榜单 WER 5.59 最优，可对标商用 API；Qwen 生态与现有大模型同族 |

| **TTS** | **dots.tts-mf**（本地部署） | 笔记/答疑朗读 | Seed-TTS-Eval 零样本：中文 WER 0.94 / SIM 80.0，4 步推理（快）；zero-shot 音色克隆（管理员预录参考音）；MF 为速度版，若需更高质感切 `dots.tts-soar`（10 步） |

替代的旧选型：FunASR（v1.0）→ 功能可用但多语言/长音频/准确率在 Qwen3-ASR 面前劣势；且 FunASR 为服务端约定，无本地可控推理。

## 为什么这么设计

1. **数据不出内网**：STT/TTS 都在内网/本机容器推理，客户沟通音频与合成音频均不出内网（合规与安全）。
2. **质量对标生产**：Qwen3-ASR 对标最强商用 API；dots.tts 在中文零样本合成接近真人。
3. **可控可升级**：模型本地部署，升级/换模型只改 `.env`（`ASR_BASE_URL` / `TTS_BASE_URL`）+ 基线表（开发文档 §4.0），不动业务代码。
4. **生态一致**：与 Qwen 家族（大模型/去噪小模型）同族，推理栈（transformers/vLLM）统一。

## 备选方案（为何没选）

- **继续用 FunASR 做 STT**：多语言与长音频能力弱于 Qwen3-ASR，且服务化约等于黑盒；无 TTS → 需另接。
- **STT/TTS 走云端 API**（如商用语音 API）：数据出内网，违规；且按量付费生产成本不可控。
- **TTS 用本地 TTS（如 edge-tts 在线版/SAPI）**：无 zero-shot 音色克隆，音色固定、自然度差；edge-tts 在线流依赖网络。
- **dots.tts-soar 作为默认**：质量更高但 10 步推理慢约 2.5 倍；MF 版 4 步在内部工具场景已足够，soar 留作 TTS 质量不达标时的切换项（5.8 降级矩阵/配置切换）。

## 核心原则

**语音能力本地自建、模型名可配置、质量对标商用、数据不出内网。**

## 关联代码（规划）

- `backend/app/services/asr.py` — `get_asr()`：`POST {ASR_BASE_URL}/v1/transcribe`（Qwen3-ASR-1.7B）
- `backend/app/services/tts.py` — `get_tts()`：`POST {TTS_BASE_URL}/v1/speak`（dots.tts-mf，`TTS_REF_AUDIO`/`TTS_REF_TEXT` 配置参考音）
- `deploy/` — STT/TTS 两个独立容器（`yika/stt`、`yika/tts`），权重挂载 `D:/models/yika/...`
- 模型权重：ASR `D:/models/yika/asr/qwen3-asr-1.7b`（已下载）；TTS `D:/models/yika/tts/dots-tts-mf`（见开发文档 §11.3 环境陷阱 7）
