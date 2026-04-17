# 🎨 ComfyUI 从入门到精通

> **适用对象**：对 AI 图像/视频生成感兴趣的同学，有基础 Python 能力更佳  
> **学习周期**：建议 2-3 周（每天 1-2 小时）  
> **前置要求**：有一台带 GPU 的电脑（建议 8GB+ 显存）

---

## 📚 课程大纲

| 章节 | 内容 | 难度 |
|------|------|------|
| [第一章：认识 ComfyUI](chapters/chapter-01-getting-started.md) | 安装、界面介绍、核心概念 | ⭐ 入门 |
| [第二章：核心节点详解](chapters/chapter-02-core-nodes.md) | LoadBalancer、CLIP、UNET、VAE、KSampler | ⭐⭐ 基础 |
| [第三章：文生图实战](chapters/chapter-03-t2i-practice.md) | Z-image Turbo 8步出图工作流 | ⭐⭐ 基础 |
| [第四章：图生视频实战](chapters/chapter-04-i2v-practice.md) | WanVideo 2.2 I2V 工作流 | ⭐⭐⭐ 中级 |
| [第五章：API 自动化](chapters/chapter-05-api-automation.md) | Python 调用 ComfyUI API | ⭐⭐⭐ 中级 |
| [第六章：生产环境部署](chapters/chapter-06-production.md) | 飞书集成、批量生成、定时任务 | ⭐⭐⭐⭐ 高级 |

---

## 🛠️ 配套资源

```
practices/
├── workflows/           # 配套工作流 JSON 文件
│   ├── zimage-turbo-t2i.json    # Z-image 文生图
│   ├── wanvideo-i2v.json        # WanVideo 图生视频
│   └── story-batch-gen.json     # 故事绘本批量生成
├── code/               # Python 代码示例
│   ├── send_workflow.py          # API 发送工作流
│   ├── poll_and_save.py          # 轮询等待结果
│   └── feishu_notify.py          # 飞书通知
assets/
└── images/             # 教程配图（截图）
```

---

## 🚀 快速开始

### 1. 安装 ComfyUI

```bash
# 克隆官方仓库
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 安装依赖
pip install -r requirements.txt

# 启动（首次会自动下载模型）
python main.py
```

访问 `http://127.0.0.1:8188` 即可看到界面。

### 2. 运行第一个工作流

1. 导入 `practices/workflows/zimage-turbo-t2i.json`
2. 输入提示词，点击「Queue Prompt」
3. 等待 10-20 秒，查看输出

### 3. 调用 API

```python
import requests
resp = requests.post("http://127.0.0.1:8188/prompt", json={"prompt": WORKFLOW})
print(resp.json())  # {"prompt_id": "..."}
```

---

## 📖 每章学习目标

### 第一章 · 认识 ComfyUI
- [ ] 理解什么是 ComfyUI 及节点式工作流
- [ ] 熟悉界面布局（节点栏、画布、队列）
- [ ] 掌握基础操作：添加节点、连接、运行

### 第二章 · 核心节点详解
- [ ] 理解 CLIP/UNET/VAE 三件套的作用
- [ ] 掌握 KSampler 的参数（steps、cfg、seed）
- [ ] 能看懂一个完整工作流的节点连接图

### 第三章 · 文生图实战
- [ ] 独立配置 Z-image Turbo 工作流
- [ ] 调参优化图像质量
- [ ] 掌握分辨率、步数、CFG 的调优思路

### 第四章 · 图生视频实战
- [ ] 理解图生视频与文生图的区别
- [ ] 掌握 WanVideo 2.2 的节点链路
- [ ] 了解 I2V 当前局限（截至 2025-04）

### 第五章 · API 自动化
- [ ] 学会用 Python 调用 `/prompt` 接口
- [ ] 掌握轮询等待结果的方法
- [ ] 能从外部系统触发 ComfyUI 生成

### 第六章 · 生产环境部署
- [ ] 集成飞书通知
- [ ] 实现批量生成流水线
- [ ] 配置定时任务

---

## ⚠️ 注意事项

1. **显存要求**：文生图 4GB+、图生视频 8GB+（WanVideo 建议 16GB）
2. **模型下载**：首次运行 ComfyUI 会自动下载基础模型（SDXL 约 5GB）
3. **版本注意**：WanVideo I2V 在 2025-04 存在架构兼容性问题，本地纯 I2V 暂不可用
4. **API 调用**：确保 ComfyUI 已启动（`python main.py`）

---

## 🔗 扩展学习资源

- [ComfyUI 官方 GitHub](https://github.com/comfyanonymous/ComfyUI)
- [ComfyUI 工作流市场](https://comfyworkflows.com/)
- [ComfyUI API 文档](https://github.com/comfyanonymous/ComfyUI#api)
- [SDXL 模型下载](https://huggingface.co/SegMind/SSD-1B)

---

*课程配套代码及工作流文件见 `practices/` 目录*
