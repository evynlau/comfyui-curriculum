# 第三章 · 文生图实战 — Z-image Turbo

> Z-image Turbo 是智谱 AI 开发的超高速文生图模型，**8 步出图**，速度比传统 SDXL 快 10 倍。

---

## 案例概述

| 项目 | 内容 |
|------|------|
| **模型** | Z-image Turbo（bf16 版本）|
| **出图速度** | 约 10-20 秒（RTX 3080）|
| **分辨率** | 最高 1024×1024 |
| **步数** | 只需 8 步 |
| **显存占用** | ~4GB |
| **特点** | 支持中文 prompt，8步即可出高质量图 |

---

## 1. 模型文件准备

确认以下文件存在于 `ComfyUI/models/` 目录：

```
models/
├── checkpoints/
│   └── z_image_turbo_bf16.safetensors     # 主模型（约 5GB）
├── vae/
│   └── ae.safetensors                      # ⚠️ 不是 qwen_image_vae！
└── text_encoders/
    └── qwen_3_4b.safetensors               # CLIP 编码器
```

> ⚠️ **关键**：VAE 必须用 `ae.safetensors`，不是默认的 `qwen_image_vae`。用错会导致全黑/全白输出。

---

## 2. 工作流节点连接图

```
CLIPLoader(104) ──────────────────────────→ CLIPTextEncode(108) ──→ ConditioningZeroOut(128)
                                                                        ↓
UNETLoader(105) ──→ LoraLoaderModelOnly(114) ──→ ModelSamplingAuraFlow(110)
                                                              ↓
EmptySD3LatentImage(107) ──────────────────→ KSampler(106) [euler, 8步]
                                                              ↓
VAELoader(103) ────────────────────────────→ VAEDecode(109) ──→ SaveImage(123)
```

### 节点详解

#### ① VAELoader (103)

```python
{
    "inputs": {"vae_name": "qwen_image_vae.safetensors"},
    "class_type": "VAELoader"
}
```

#### ② CLIPLoader (104)

```python
{
    "inputs": {
        "clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        "type": "qwen_image",
        "device": "default"
    },
    "class_type": "CLIPLoader"
}
```

#### ③ UNETLoader (105)

```python
{
    "inputs": {
        "unet_name": "qwen_image_2512_fp8_e4m3fn.safetensors",
        "weight_dtype": "default"
    },
    "class_type": "UNETLoader"
}
```

#### ④ LoraLoaderModelOnly (114)

```python
{
    "inputs": {
        "lora_name": "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
        "strength_model": 1,
        "model": ["105", 0]
    },
    "class_type": "LoraLoaderModelOnly"
}
```

> ⚠️ **关键**：Turbo 模型需要 LoRA 加速！缺少这个节点会非常慢。

#### ⑤ ModelSamplingAuraFlow (110)

```python
{
    "inputs": {
        "model": ["114", 0],
        "shift": 3
    },
    "class_type": "ModelSamplingAuraFlow"
}
```

#### ⑥ CLIPTextEncode (108) — 正向提示词

```python
{
    "inputs": {
        "text": "一只穿着宇航服的橘猫，漂浮在太空中，背景是蓝色地球，科幻风格，高清细节",
        "clip": ["104", 0]
    },
    "class_type": "CLIPTextEncode"
}
```

#### ⑦ ConditioningZeroOut (128) — 负向条件

```python
{
    "inputs": {
        "conditioning": ["108", 0]
    },
    "class_type": "ConditioningZeroOut"
}
```

#### ⑧ EmptySD3LatentImage (107)

```python
{
    "inputs": {
        "width": 1328,
        "height": 1328,
        "batch_size": 1
    },
    "class_type": "EmptySD3LatentImage"
}
```

> ⚠️ Z-image Turbo 原生分辨率为 1328×1328，不是 1024×1024！

#### ⑨ KSampler (106)

```python
{
    "inputs": {
        "model": ["110", 0],
        "positive": ["108", 0],
        "negative": ["128", 0],
        "latent_image": ["107", 0],
        "seed": 9527000,
        "steps": 8,
        "cfg": 1,
        "sampler_name": "euler",
        "scheduler": "simple",
        "denoise": 1.0
    },
    "class_type": "KSampler"
}
```

> ⚠️ **重要**：Turbo 模型用 **euler** 采样器，**不是** res_multistep！

#### ⑩ VAEDecode (109)

```python
{
    "inputs": {
        "samples": ["106", 0],
        "vae": ["103", 0]
    },
    "class_type": "VAEDecode"
}
```

#### ⑪ SaveImage (123)

```python
{
    "inputs": {
        "filename_prefix": "zimage_result",
        "images": ["109", 0]
    },
    "class_type": "SaveImage"
}
```

---

## 3. 提示词调优指南

### 中文 vs 英文

Z-image 支持中文 prompt，但英文效果通常更好。

```python
# 中文（可用）
"一只穿着宇航服的橘猫漂浮在太空中"

# 英文（效果更好）
"an orange cat in astronaut suit floating in space, blue earth background, sci-fi style, high detail"
```

### 质量增强词

在 prompt 末尾添加质量词可以提升效果：

```
# 推荐后缀
", masterpiece, best quality, high detail, 8k, photorealistic"

# 不良词汇（会适得其反）
"very very very", "absurdres", 过多感叹号
```

### 风格控制

```python
# 写实风格
"photo, realistic, natural lighting"

# 动漫风格
"anime style, vibrant colors, cel shading"

# 数字艺术
"digital art, illustration, concept art"
```

---

## 4. 参数对照表

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| 分辨率 | 1024×1024 | Z-image 在此分辨率最优 |
| 步数 | 8 | 8步足够，更多步无明显提升 |
| CFG | 1.0 | Z-image 固定 1.0 |
| 采样器 | res_multistep | 专为 Z-image 设计 |
| 调度器 | simple | Z-image 专用 |
| Seed | 任意 | 固定 seed 可复现 |

---

## 5. 常见错误排查

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `bad_linked_input, must be a length-2 list` | CLIPTextEncode 的 clip 传了文件名 | 改为 `["57:30", 0]` |
| `Required input missing: unet_name` | UNETLoader 用了 `model_name` | 改为 `unet_name` |
| `Required input missing: weight_dtype` | UNETLoader 缺少字段 | 加 `"weight_dtype": "default"` |
| `400 prompt_outputs_failed_validation` | 节点 ID 冲突/链路断 | 检查所有连接 |
| `type must be lumina2` | CLIPLoader 的 type 设错 | 改为 `"type": "lumina2"` |
| 生成图全黑/全白 | VAE 用错了 | 用 `ae.safetensors` |

---

## 6. 课后练习

### 练习 1：生成第一张图
按照上述步骤，生成一张「穿宇航服的橘猫」图片。

### 练习 2：探索不同风格
固定 `seed=9527000`，尝试以下风格：
- 动漫风格
- 写实风格
- 赛博朋克风格

### 练习 3：提高分辨率
尝试 512×512 vs 1024×1024，对比细节差异。

### ⭐ 挑战任务
编写一个 Python 脚本，批量生成 4 张不同提示词的图片（seed 递增），并保存到本地。
