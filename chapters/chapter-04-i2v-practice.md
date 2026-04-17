# 第四章 · 图生视频实战 — WanVideo 2.2

> WanVideo 是通义万相团队开发的视频生成模型，ComfyUI 版本支持文生视频（T2V）和图生视频（I2V）。

---

## ⚠️ 重要前置说明（2025-04 更新）

**WanVideo 2.2 本地纯 I2V（图生视频）存在架构兼容性问题**：

| 组件 | 状态 | 原因 |
|------|------|------|
| WanVideo T2V（文生视频）| ✅ 可用 | 已验证参数正确 |
| WanVideo I2V（图生视频）| ❌ 暂不可用 | `WanVideoEncode` 输出通道数与 `WanVideoSampler` 期望不匹配 |
| WanImageToVideoApi 封装节点 | ❌ 需要云端 | 依赖 `https://api.comfy.org` |
| CreateVideo 合成幻灯片 | ✅ 可用 | 将 T2I 图片序列合成为幻灯片视频 |

**本章提供两种方案**：
1. **T2I + 幻灯片合成**：用 ComfyUI 生成关键帧图，再用 CreateVideo 合成为视频（✅ 可用）
2. **WanVideo I2V 节点详解**：记录底层节点结构，供后续官方修复后使用

---

## 方案 A：图片序列 → 视频（立即可用）

### 工作流

```
[场景1 Prompt] → [Z-image/SD] → SaveImage ─┐
[场景2 Prompt] → [Z-image/SD] → SaveImage ─┼→ [VHS_VideoCombine] → 视频文件
[场景3 Prompt] → [Z-image/SD] → SaveImage ─┘
```

### 步骤

1. **生成关键帧图片**（用第三章的 Z-image 工作流）

```python
scenes = [
    {"name": "scene01_start", "prompt": "山间日出，薄雾环绕，远景，温暖光线"},
    {"name": "scene02_action", "prompt": "一只白狐在雪地奔跑，特写，动感模糊"},
    {"name": "scene03_climax", "prompt": "白狐回头望向镜头，雪花飘落，电影感"}
]
```

2. **使用 VHS_VideoCombine**

```python
{
    "inputs": {
        "images": [["LoadImage节点", 0], ...],  # 所有帧图片
        "frame_rate": 24,
        "loop_count": 0,       # 0 = 不循环
        "filename": "my_video",
        "format": "video/h264-mp4",
        "quality": 80
    },
    "class_type": "VHS_VideoCombine"
}
```

3. **连接 SaveImage 或 VHS_VideoCombine**

```
[LoadImage] ──┐
[LoadImage] ──┼──→ [VHS_VideoCombine] → 保存视频
[LoadImage] ──┘
```

---

## 方案 B：WanVideo 底层节点详解（参考）

> 以下是截至 2025-04 已验证的 WanVideo 2.2 I2V 底层节点结构。**本地 I2V 因架构兼容性问题暂不可用**，仅供学习参考。

### 节点连接图

```
LoadImage → ImageResizeKJv2 → WanVideoEncode(vae+image) → LATENT
                                                          ↓
                                                  WanVideoEmptyEmbeds(extra_latents=LATENT)
                                                  输出 WANVIDIMAGE_EMBEDS
                                                               ↓
LoadWanVideoT5TextEncoder → WanVideoTextEncode(positive_prompt+negative_prompt+t5)
输出 WANVIDEOTEXTEMBEDS                            输出 WANVIDEOTEXTEMBEDS
                                                               ↓
WanVideoModelLoader ──────────────────────────────────────────→ WanVideoSampler
WanVideoTorchCompileSettings → WANCOMPILEARGS ───────────────↗
WanVideoSLG → SLGARGS ───────────────────────────────────────↗
WanVideoEasyCache → CACHEARGS ────────────────────────────────↗
WanVideoExperimentalArgs(raag_alpha=0) ───────────────────────↗
                              (WANVIDIMAGE_EMBEDS + WANVIDEOTEXTEMBEDS)
                                    ↓ LATENT
                              WanVideoDecode(vae+LATENT) → IMAGE → SaveImage
```

### 节点 ID 分配参考

| 节点ID | 类型 | 说明 |
|--------|------|------|
| 10 | LoadImage | 加载关键帧图片 |
| 71 | ImageResizeKJv2 | 缩放图片 |
| 38 | WanVideoVAELoader | VAE 加载器 |
| 70 | WanVideoEncode | 图片→latent 编码 |
| 78 | WanVideoEmptyEmbeds | 空 latent（含 extra_latents）|
| 22 | WanVideoModelLoader | 主模型 |
| 35 | WanVideoTorchCompileSettings | Torch Compile |
| 11 | LoadWanVideoT5TextEncoder | T5 文本编码器 |
| 16 | WanVideoTextEncode | 文本 embedding |
| 91 | WanVideoSLG | SLG 层级引导 |
| 94 | WanVideoEasyCache | 缓存加速 |
| 90 | WanVideoExperimentalArgs | 实验参数 |
| 27 | WanVideoSampler | 核心采样器 |
| 28 | WanVideoDecode | VAE 解码 |
| 9 | SaveImage | 保存帧 |

### 关键参数

#### WanVideoVAELoader
```python
{
    "inputs": {
        "model_name": "Wan2_2_VAE_bf16.safetensors",
        "precision": "bf16"   # ⚠️ required，不是 optional
    }
}
```

#### WanVideoEncode
```python
{
    "inputs": {
        "vae": ["38", 0],
        "image": ["71", 0],
        "enable_vae_tiling": False,
        "tile_x": 272,
        "tile_y": 272,
        "tile_stride_x": 144,   # ⚠️ 不能用 64，太小
        "tile_stride_y": 128
    }
}
```

#### WanVideoEmptyEmbeds
```python
{
    "inputs": {
        "width": 848,
        "height": 480,
        "num_frames": 121,
        "extra_latents": ["70", 0]   # Encode → LATENT
    }
}
```

#### WanVideoTextEncode
```python
{
    "inputs": {
        "positive_prompt": "正向提示词",
        "negative_prompt": "",   # ⚠️ required！不可省略
        "t5": ["11", 0],
        "force_offload": True
    }
}
```

#### WanVideoSampler
```python
{
    "inputs": {
        "model": ["22", 0],
        "image_embeds": ["78", 0],
        "text_embeds": ["16", 0],
        # ⚠️ samples: 不连接！用 extra_latents 传图信息
        "steps": 30,
        "cfg": 5.0,
        "shift": 8.0,
        "seed": 12345,
        "force_offload": True,
        "scheduler": "flowmatch_pusa",
        "riflex_freq_index": 0,
        "slg_args": ["91", 0],
        "cache_args": ["94", 0],
        "experimental_args": ["90", 0]
    }
}
```

### ⚠️ 踩坑记录

| 错误 | 错误信息 | 解决方案 |
|------|---------|----------|
| 模型名错误 | 400 error | 用 `Wan2_2-TI2V-5B-Turbo_fp16.safetensors` |
| precision 缺失 | Required input missing | 加 `"precision": "bf16"` |
| negative_prompt 缺失 | Required input missing | 加 `"negative_prompt": ""` |
| pad_color 格式错误 | type error | 用字符串 `"0, 0, 0"` 而非数组 |
| keep_proportion 格式错误 | invalid value | 用字符串 `"resize"` 而非布尔值 |
| tile_stride 太小 | 编码质量差 | 用 144×128 而非 64×64 |

---

## 视频生成参数指南

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 分辨率 | 848×480 | WanVideo 推荐分辨率 |
| 帧数 | 121 | 5秒 @ 24fps |
| 步数 | 30 | 质量和速度平衡 |
| CFG | 5.0 | 建议范围 3.0-7.0 |
| Shift | 8.0 | 影响运动幅度 |
| 采样器 | flowmatch_pusa | WanVideo 专用 |

---

## 课后练习

### 练习 1：生成故事关键帧（立即可用）
为「雪山救狐狸」故事生成 4 个关键帧：
1. 场景：雪山脚下，远景
2. 人物：探险家发现白狐
3. 动作：白狐在雪地奔跑
4. 结尾：夕阳下的告别

### 练习 2：合成幻灯片视频
用 VHS_VideoCombine 将 4 张图片合成为视频。

### ⭐ 挑战任务
编写 Python 脚本，实现：
1. 批量生成 N 个场景的图片
2. 自动合成视频
3. 添加 TTS 配音（参考 edge-tts）

---

## 本章小结

| 方案 | 状态 | 适用场景 |
|------|------|----------|
| T2I + VHS_VideoCombine | ✅ 可用 | 故事分镜、幻灯片视频 |
| WanVideo I2V | ❌ 暂不可用 | 等待架构修复 |
| WanVideo T2V | ✅ 可用 | 直接文生视频 |
