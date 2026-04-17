# 第二章 · 核心节点详解

> 本章深入讲解 ComfyUI 中最核心的 5 类节点。理解它们，你就能读懂任何工作流。

---

## 节点家族全景图

```
📦 Loaders（加载器）
├── CheckpointLoader         加载 SD 模型（包含 CLIP/UNET/VAE 三合一）
├── CLIPLoader              单独加载 CLIP 模型
├── UNETLoader              单独加载 UNet 模型
├── VAELoader               单独加载 VAE 模型
└── UpscaleModelLoader      加载超分辨率模型

🔄 Sampling（采样）
├── KSampler                核心采样器（文生图/图生图）
├── KSamplerSelect          选择采样算法
├── ModelSamplingSDXL      SDXL 专用采样匹配
└── SamplerCustom           自定义采样器

✏️ Conditioning（条件）
├── CLIPTextEncode          文本 → 提示词向量
├── CLIPTextEncodeSDXL      SDXL 专用编码器
├── ConditioningCombine    合并多个条件
├── ConditioningZeroOut    否定条件（清零正向）
└── ControlNetApply        应用 ControlNet 控制

🎨 Image（图像处理）
├── VAEEncode               图像 → latent
├── VAEDecode               latent → 图像
├── ImageScale              缩放图片
├── ImagePad                填充图片
├── ImageBlur               模糊
├── ImageSharpen            锐化
└── SaveImage               保存图片

📹 Video（视频处理）
├── VHS_VideoCombine        图片序列 → 视频
├── VHS_VideoLoad           加载视频
└── LoadVideoFromFile       从文件加载视频帧
```

---

## 1. Loaders（加载器）

### CheckpointLoader — 一键加载完整模型

SD 模型文件（.safetensors/.ckpt）通常包含三个部分：

```
sd_xl_base_1.0.safetensors
├── CLIP 模型（文本理解）
├── UNET 模型（扩散生成）
└── VAE 模型（编码/解码）
```

**CheckpointLoader** 一次性把它们全部加载：

| 参数 | 说明 |
|------|------|
| `checkpoint` | 选择模型文件（从 `models/checkpoints/` 目录） |

**输出端口：**
| 端口 | 类型 | 去向 |
|------|------|------|
| `model` | MODEL | → KSampler |
| `clip` | CLIP | → CLIPTextEncode |
| `vae` | VAE | → VAEDecode / VAEEncode |

### VAELoader — 单独加载 VAE

VAE 负责编码和解码。有些模型自带 VAE，有些需要单独加载。

```python
# VAELoader 的典型用法
{
    "inputs": {"vae_name": "ae.safetensors"},
    "class_type": "VAELoader"
}
```

> ⚠️ **注意**：不同模型要用对应的 VAE，混用会导致生成全黑/全白图。

### CLIPLoader — 单独加载 CLIP

CLIP 负责理解文本。常见场景：
- SD 1.5 用 `sd1x/clip_g.safetensors`
- SDXL 用 `sd_xl_clip_[g]/safetensors`
- 某些特殊模型（如 Z-image）需要特定 CLIP

```python
# Z-image Turbo 的 CLIP 设置
{
    "inputs": {
        "clip_name": "qwen_3_4b.safetensors",
        "type": "lumina2"   # ⚠️ 必须匹配模型类型
    },
    "class_type": "CLIPLoader"
}
```

---

## 2. Conditioning（条件编码）

### CLIPTextEncode — 文本转向量

这是连接「人类语言」和「AI 神经网络」的桥梁：

```
"一只橘色的猫在晒太阳"  →  CLIPTextEncode  →  [提示词向量]
                                                        ↓
                                              KSampler 正面条件
```

**参数：**
| 参数 | 说明 |
|------|------|
| `text` | 你的提示词（支持英文效果更好，中文也行） |
| `clip` | 从 CLIPLoader 输入 |

**Negative Prompt（负面提示词）**

通常我们会连接两个 CLIPTextEncode：
- **Positive（正向）**：你想要的效果
- **Negative（负向）**：你不想要的效果

```python
# 典型负面提示词组合
negative = "low quality, blurry, watermark, text, logo, username, deformed, ugly"
```

### ConditioningZeroOut — 清零条件

用于**否定**已编码的条件：

```
CLIPTextEncode(positive) → ConditioningZeroOut → KSampler(negative)
```

**作用**：把正向条件清零，等价于「什么都不加」。常用于 Z-image 这类不需要传统负向提示词的模型。

---

## 3. Sampling（采样）

### KSampler — 核心心脏

KSampler 是 ComfyUI 最重要、最复杂的节点：

```
输入：
├── model           从 CheckpointLoader 或 UNETLoader
├── positive        从 CLIPTextEncode（正向条件）
├── negative        从 CLIPTextEncode（负向条件）
└── latent_image    从 Empty Latent Image 或 VAEEncode

参数：
├── seed            随机种子（固定种子 = 相同结果）
├── steps           采样步数（20-30 常用）
├── cfg             引导强度（1-20，越高越贴合提示词）
├── sampler_name    采样算法
└── scheduler       调度器

输出：
└── latent          采样结果（潜在空间图像）
```

#### seed（种子）

- **相同 seed + 相同参数 = 相同结果**（可复现）
- 不同 seed 会产生变化
- ✏️ **技巧**：记住你喜欢的图的 seed，下次用相同 seed 微调提示词

#### steps（步数）

| steps | 效果 | 速度 |
|-------|------|------|
| 1-5 | 草稿，细节模糊 | ⚡ 极快 |
| 10-15 | 可用，有一定细节 | 快速 |
| 20-30 | 推荐，细节和速度平衡 | 中等 |
| 50+ | 极精细（通常看不出区别） | 慢 |

#### cfg（引导强度）

| cfg 值 | 效果 |
|--------|------|
| 1-3 | 自由度大，随机性强 |
| 5-8 | **推荐值**，贴合提示词又不失创意 |
| 10-15 | 非常贴合，可能过饱和/变形 |
| 20+ | 严重过拟合，不推荐 |

#### sampler_name（采样算法）

| 采样器 | 特点 | 推荐场景 |
|--------|------|----------|
| `euler` | 平衡，快速 | ✅ 通用首选 |
| `euler_ancestral` | 有变化，每步加噪 | 图生图/风格化 |
| `dpm_2` | 精细 | 高分辨率 |
| `dpmpp_2m` | 省显存 | 低显存机器 |
| `ddpm` | 传统 | 学术/测试 |

#### scheduler（调度器）

控制噪声减少的节奏：

| 调度器 | 特点 |
|--------|------|
| `normal` | 线性递减 |
| `simple` | Z-image 专用 |
| `karras` | 开始快，后面慢，细节好 |

---

## 4. Latent（潜在空间）

### Empty Latent Image — 创建空白 Latent

文生图时，从零开始生成：

```python
{
    "inputs": {
        "width": 1024,
        "height": 1024,
        "batch_size": 1   # 同时生成几张
    },
    "class_type": "Empty Latent Image"
}
```

**分辨率建议：**
- SD 1.5：512×512 最优
- SDXL / Z-image：1024×1024
- WanVideo：848×480

> ⚠️ 分辨率必须是 8 的倍数（因为 VAE 的下采样因子是 8）

### VAEEncode — 图像编码为 Latent

图生图时，把真实图片编码进潜在空间：

```
[LoadImage] → [VAEEncode] → [KSampler] → [VAEDecode] → [SaveImage]
```

### VAEDecode — Latent 解码为图像

把 KSampler 输出解码成可见图片：

```
[samples from KSampler] → [VAEDecode] → [IMAGE] → [SaveImage]
```

---

## 5. 节点连接图解

### 完整文生图工作流

```
┌─────────────────┐
│ CheckpointLoader│
│ sd_xl_base.safetensors│
└───────┬────┬────┘
        │    │
        ↓    ↓
    ┌───────┐ │   ┌──────────────┐
    │  CLIP │ │   │ Empty Latent │
    └───┬───┘ │   └──────┬───────┘
        │     │          │
        ↓     │          ↓
  ┌───────────┴──┐      │
  │ CLIPTextEnc + │      │
  │ CLIPTextEnc - │      │
  └──────┬───┬───┘      │
         ↓   ↓          ↓
       [KSampler]
            ↓ samples
        [VAEDecode]
            ↓ image
        [SaveImage]
```

### 进阶：图生图（Img2Img）

```
┌──────────┐     ┌───────────┐
│LoadImage │────→│ VAEEncode │
└──────────┘     └─────┬─────┘
                       ↓ latent_image
                 [KSampler] ← 用 denoise < 1.0
                       ↓ samples
                  [VAEDecode]
```

> 💡 **denoise 参数**：0.0 = 完全不变，1.0 = 完全重新生成。0.7-0.9 是常用范围。

---

## 节点查找技巧

### 搜索不到节点？

1. **检查大小写**：`SaveImage` 不是 `Saveimage`
2. **完整输入**：`Empty Latent Image` 要全拼
3. **右键菜单**：在画布空白处右键 → Add Node → 完整分类树

### 节点版本

ComfyUI 更新会导致节点参数变化。如果加载旧工作流报错：
- 查看节点右侧 ⚙️ 图标，确认参数是否齐全
- 或更新 ComfyUI 到最新版本

---

## 本章小结

| 节点类别 | 核心作用 |
|----------|----------|
| Loader | 加载模型（Checkpoint = CLIP+UNET+VAE 三合一）|
| Conditioning | 把文字/图像转成 AI 能理解的「条件向量」|
| KSampler | 核心采样器，seed/steps/cfg 三参数最重要 |
| Latent | 潜在空间图像，是生成的中介态 |
| VAE | 编码（图像→潜在）和解码（潜在→图像）|

---

## 课后练习

1. ✅ 绘制完整文生图工作流的节点连接图（不需要实际跑）
2. ✅ 理解 seed/steps/cfg 三个参数对结果的影响
3. ⭐ 固定 seed，改变 steps（5/15/25），对比三张图差异
4. ⭐ 固定 seed=42，cfg 分别设为 3/7/15，对比效果
