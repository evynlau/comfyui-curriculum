# 第一章 · 认识 ComfyUI

## 什么是 ComfyUI？

ComfyUI 是一个**基于节点的工作流工具**，用于 AI 图像和视频生成。它的核心特点：

| 特点 | 说明 |
|------|------|
| 🎨 节点式界面 | 把生成过程拆成多个可组合的「节点」 |
| ⚡ 高效 | 比 WebUI 占用更少显存，速度更快 |
| 🔧 高度可定制 | 任意节点可替换、组合、调参 |
| 💾 工作流可保存 | 每个 .json 文件就是一个完整工作流 |
| 🌐 API 支持 | 通过 REST API 从代码触发生成 |

> 💡 **类比**：如果把 AI 生图比作「做菜」，ComfyUI 就是把所有厨具（切菜刀、炉灶、烤箱）摊在面前，你可以自由组合每一步用什么工具。

---

## 系统要求

```
硬件：
- 显卡：NVIDIA，8GB+ 显存（文生图 4GB 可跑）
- 内存：16GB+
- 硬盘：20GB+ 可用空间

软件：
- Python 3.10 ~ 3.12
- CUDA 11.8 或 12.1
- Windows / Linux / macOS（macOS 用 MPS 后端）
```

---

## 安装步骤

### 方法一：从零安装（推荐）

```bash
# 1. 克隆官方仓库
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动（首次会自动下载基础模型）
python main.py
```

### 方法二：便携版（Windows）

下载 ComfyUI_windows_portable_nvidia.7z，解压即用，无需安装 Python。

### 验证是否安装成功

启动后访问：
```
http://127.0.0.1:8188
```

看到节点编辑界面即为成功 ✅

---

## 界面介绍

```
┌─────────────────────────────────────────────────────────────────┐
│  Menu Bar: [Queue Prompt] [Interrupt] [Clear] [Save] [Load]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                               │
│  │  Node Tree  │     ← 左侧：所有可用节点列表                 │
│  │  (搜索框)   │                                               │
│  │             │                                               │
│  │  Loaders    │     ← 按类别分组                             │
│  │  Sampling   │                                               │
│  │  Conditioning                                               │
│  │  ...        │                                               │
│  └─────────────┘     ┌──────────────────────────┐             │
│                      │       Canvas              │             │
│                      │  （中间：节点画布）       │             │
│                      │                          │             │
│                      │   [LoadImage]──→[CLIP]   │             │
│                      │        ↓                  │             │
│                      │   [UNET] ───→[Sampler]   │             │
│                      │        ↓                  │             │
│                      │   [VAE]  ───→[Decode]     │             │
│                      │        ↓                  │             │
│                      │     [SaveImage]           │             │
│                      └──────────────────────────┘             │
├─────────────────────────────────────────────────────────────────┤
│  Status: Ready │ VRAM: 4.2GB/8GB │ Queue: 0  ← 底部状态栏      │
└─────────────────────────────────────────────────────────────────┘
```

### 核心区域

| 区域 | 作用 |
|------|------|
| **Node Tree（左侧栏）** | 搜索和浏览所有节点 |
| **Canvas（中间）** | 放置节点、连接线、编辑工作流 |
| **Queue（底部）** | 执行队列和历史记录 |
| **Menu Bar** | 保存/加载/执行等操作 |

---

## 基础操作

### 添加节点
1. **方法一**：双击画布空白处，弹出节点搜索框，输入节点名
2. **方法二**：从左侧栏拖拽节点到画布

### 连接节点
- 从一个节点的**输出端口**（右侧圆点）拖拽到另一个的**输入端口**（左侧圆点）
- 端口颜色匹配才可连接：
  - 🔵 `MODEL` → 🔵 输入
  - 🟢 `CONDITIONING` → 🟢 输入
  - 🟠 `LATENT` → 🟠 输入
  - 🟣 `IMAGE` → 🟣 输入

### 断开连接
- 右键连接线 → Delete
- 或点击节点按 `Delete` 键

### 运行工作流
- 点击 Menu Bar 的 **「Queue Prompt」**（或快捷键 `Ctrl+Enter`）
- 底部状态栏显示进度

---

## 第一个工作流：极简文生图

### 目标
用最少的节点，生成一张 AI 图片

### 需要用到的节点

| 节点 | 作用 |
|------|------|
| `CLIP Text Encode` | 把文字转成 AI 能理解的「提示词向量」 |
| `Empty Latent Image` | 创建一个空白的「潜在图像」（等待被填充） |
| `KSampler` | 核心采样器，实际执行生成 |
| `VAE Decode` | 把「潜在图像」解码成真正的图片 |
| `Save Image` | 保存图片到本地 |

### 最小工作流

```
[CLIPLoader]
      ↓ clip
[CLIPTextEncode(positive)] ──→ [KSampler +]
[CLIPTextEncode(negative)] ──→ [KSampler -]
                                  ↓ latent
[Empty Latent Image]  ──────────→ [KSampler]
                                  ↓ samples
                               [VAEDecode]
                                  ↓ image
                              [SaveImage]
```

> 📝 **提示**：还需要一个 `VAELoader` 给 VAEDecode 提供解码器。

### 操作步骤

1. **添加 `CLIPLoader`**
   - `clip_name`: 选择你的 CLIP 模型（如 `sd_xl(clip).safetensors`）

2. **添加两个 `CLIPTextEncode`**
   - 第一个：输入正向提示词（如 `a cute cat, digital art`）
   - 第二个：输入负向提示词（如 `low quality, blurry`）

3. **添加 `Empty Latent Image`**
   - 设置 `width`: 1024, `height`: 1024

4. **添加 `KSampler`**
   - `steps`: 20（步数越多越精细，默认 20-30）
   - `cfg`: 7.0（引导强度，7 左右效果较好）
   - `sampler_name`: `euler`（常用采样器）

5. **添加 `VAELoader`** 和 **`VAEDecode`**

6. **添加 `SaveImage`**

7. 点击 **「Queue Prompt」**，等待结果！

---

## 概念解释：什么是 Latent（潜在空间）？

这是 ComfyUI（和 Stable Diffusion）最核心的概念：

```
真实图片 (512x512x3 = 786,432 像素)
      ↓ VAE 编码
潜在空间 (64x64x4 = 16,384 数值)  ← AI 在这里「做梦」
      ↓ VAE 解码
真实图片
```

**为什么需要 latent？**
- 直接在像素层面操作图片，计算量巨大（SDXL 要处理 512×512×3 = 78万个像素）
- 潜在空间只有 64×64×4 = 1.6万个数值，计算快 **24倍**
- AI 其实是在「潜在空间」里「做梦」，最后才解码成图片

> 🎯 理解这一点对后续调试非常重要：如果你的图生成出来是黑屏或全白，很可能是 VAE 或 Latent 连接出了问题。

---

## 常见问题

### Q: 点击 Queue 后没反应？
检查底部状态栏是否报错。常见原因：
- 节点连接不完整（有断开的线）
- 模型文件不存在或路径错误

### Q: 显存不足（CUDA out of memory）？
- 降低分辨率（如从 1024×1024 降到 768×768）
- 减少 batch_size（批处理数量）
- 开启模型卸载：`Settings → VRAM → low`

### Q: 生成速度很慢？
- 使用较短的步数（steps: 20 足够）
- 选择更快的采样器（如 `euler`, `euler_ancestral`）
- 升级到更强显卡

---

## 本章小结

| 概念 | 关键点 |
|------|--------|
| ComfyUI | 节点式工作流工具，可组合、可保存、可 API 调用 |
| Latent | 潜在空间，AI 在这里生成，后由 VAE 解码成图片 |
| 节点连接 | 按类型匹配（颜色），从输出拖到输入 |
| 最小工作流 | CLIP → Empty Latent → KSampler → VAEDecode → SaveImage |

---

## 课后练习

1. ✅ 安装 ComfyUI 并成功启动
2. ✅ 在画布上添加 5 个节点（不需要连接）
3. ✅ 构建一个极简文生图工作流并成功生成图片
4. ⭐ 挑战：把分辨率改成 512×512，观察生成速度变化
