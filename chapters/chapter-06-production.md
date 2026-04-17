# 第六章 · 生产环境部署

> 从个人使用到团队协作：飞书集成、批量流水线、定时任务。

---

## 1. 整体架构

```
用户（飞书/终端）
    ↓ 触发
[Python 脚本] → [ComfyUI API] → [生成图片]
    ↓
[飞书通知] ← [结果处理]
```

---

## 2. 环境准备

### 目录结构

```
ai_t2i_project/
├── app.py              # Flask 后端
├── comfy_orchestrance.py # ComfyUI 调度脚本
├── send_message_tool.py # 飞书发送工具
├── workflows/          # 工作流 JSON
│   ├── zimage-turbo-t2i.json
│   ├── wanvideo-i2v.json
│   └── story-batch-gen.json
├── temp/               # 临时文件
└── start_all.sh        # 一键启动脚本
```

### 飞书配置

```python
# send_message_tool.py
import requests, json

# 从 ~/.hermes/.env 读取飞书凭证
LARK_APP_ID = "cli_xxx"
LARK_APP_SECRET = "xxx"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": LARK_APP_ID, "app_secret": LARK_APP_SECRET})
    return resp.json()["tenant_access_token"]

def send_image_to_feishu(chat_id, image_path, msg=""):
    """发送图片到飞书"""
    token = get_tenant_access_token()
    
    # 1. 上传图片获取 image_key
    url = "https://open.feishu.cn/open-apis/im/v1/images"
    headers = {"Authorization": f"Bearer {token}"}
    with open(image_path, "rb") as f:
        files = {"image_type": "message", "image": f}
        r = requests.post(url, headers=headers, files=files)
    image_key = r.json()["data"]["image_key"]
    
    # 2. 发送消息
    msg_url = "https://open.feishu.cn/open-apis/im/v1/messages"
    payload = {
        "receive_id": chat_id,
        "msg_type": "image",
        "content": json.dumps({"image_key": image_key})
    }
    if msg:
        payload = {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": msg})
        }
    
    requests.post(msg_url, headers=headers, json=payload)
```

---

## 3. ComfyUI 调度脚本

### comfy_orchestrance.py

```python
#!/usr/bin/env python3
"""
ComfyUI 图像生成调度器
用法: python comfy_orchestrance.py <workflow_json> <prompt> [output_prefix]
"""

import sys
import json
import time
import requests
from pathlib import Path

COMFYU_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = Path.home() / "work/ComfyUI/output"

def load_workflow(json_path):
    with open(json_path) as f:
        return json.load(f)

def set_prompt(workflow, prompt_text, seed=None):
    """修改工作流中的提示词"""
    for node_id, node in workflow.items():
        if node["class_type"] == "CLIPTextEncode":
            node["inputs"]["text"] = prompt_text
        if seed and node["class_type"] == "KSampler":
            node["inputs"]["seed"] = seed
    return workflow

def send_and_wait(workflow, poll_interval=3, max_wait=600):
    """发送工作流并等待结果"""
    resp = requests.post(f"{COMFYU_URL}/prompt", json={"prompt": workflow}, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]
    print(f"已提交: {prompt_id}")
    
    for _ in range(max_wait // poll_interval):
        time.sleep(poll_interval)
        h = requests.get(f"{COMFYU_URL}/history/{prompt_id}", timeout=10).json()
        if prompt_id in h:
            status = h[prompt_id]["status"]["status_str"]
            print(f"状态: {status}")
            if status == "success":
                imgs = []
                for out in h[prompt_id]["outputs"].values():
                    imgs.extend(out.get("images", []))
                return imgs
            elif status == "failed":
                raise Exception(f"失败: {h[prompt_id]['status'].get('errors')}")
    raise TimeoutError("超时")

def main():
    if len(sys.argv) < 3:
        print("用法: python comfy_orchestrance.py <workflow.json> <prompt>")
        sys.exit(1)
    
    workflow_path = sys.argv[1]
    prompt = sys.argv[2]
    output_prefix = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    workflow = load_workflow(workflow_path)
    workflow = set_prompt(workflow, prompt)
    
    imgs = send_and_wait(workflow)
    
    # 打印结果
    for img in imgs:
        print(f"图片: {img['filename']}")
        print(f"URL: {COMFYU_URL}/view?filename={img['filename']}")
    
    return [img["filename"] for img in imgs]

if __name__ == "__main__":
    main()
```

---

## 4. 批量故事绘本生成

### story-batch-gen.json 工作流

```json
{
    "nodes": [
        {
            "id": 1,
            "type": "CLIPLoader",
            "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "lumina2"}
        },
        {
            "id": 2,
            "type": "UNETLoader",
            "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}
        },
        {
            "id": 3,
            "type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"}
        }
    ]
}
```

### 批量生成脚本

```python
#!/usr/bin/env python3
"""
批量故事绘本生成器
读取 scenes.json 中的场景列表，批量生成图片
"""

import json
import time
import requests
from pathlib import Path

STORY_CONFIG = "scenes.json"  # 包含场景列表的配置文件
WORKFLOW = "workflows/story-batch-gen.json"
COMFYU_URL = "http://127.0.0.1:8188"

class StoryGenerator:
    def __init__(self):
        self.scenes = self.load_scenes()
    
    def load_scenes(self):
        with open(STORY_CONFIG) as f:
            return json.load(f)["scenes"]
    
    def generate_scene(self, scene):
        """生成单个场景"""
        print(f"生成场景: {scene['name']} - {scene['prompt']}")
        
        workflow = self.build_workflow(scene)
        imgs = self.send_and_wait(workflow)
        
        return {
            "scene": scene["name"],
            "images": imgs,
            "prompt": scene["prompt"]
        }
    
    def build_workflow(self, scene):
        """构建工作流"""
        # ... 参考第三章的工作流构建
        pass
    
    def send_and_wait(self, workflow, poll_interval=3):
        resp = requests.post(f"{COMFYU_URL}/prompt", json={"prompt": workflow}, timeout=30)
        prompt_id = resp.json()["prompt_id"]
        
        for _ in range(200):  # 最多等 10 分钟
            time.sleep(poll_interval)
            h = requests.get(f"{COMFYU_URL}/history/{prompt_id}").json()
            if prompt_id in h and h[prompt_id]["status"]["status_str"] == "success":
                return [img["filename"] for img in 
                        h[prompt_id]["outputs"].get("9", {}).get("images", [])]
        return []
    
    def run(self, start_idx=0, end_idx=None):
        """运行批量生成"""
        end_idx = end_idx or len(self.scenes)
        results = []
        
        for i, scene in enumerate(self.scenes[start_idx:end_idx]):
            try:
                result = self.generate_scene(scene)
                results.append(result)
            except Exception as e:
                print(f"场景 {scene['name']} 失败: {e}")
                results.append({"scene": scene["name"], "error": str(e)})
        
        return results

if __name__ == "__main__":
    generator = StoryGenerator()
    results = generator.run()
    
    # 保存结果
    with open("generation_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"完成！共生成 {len(results)} 个场景")
```

---

## 5. 一键启动脚本

### start_all.sh

```bash
#!/bin/bash

# ComfyUI 启动脚本
echo "启动 ComfyUI..."
cd /home/evynlau/work/ComfyUI
python main.py --enable-cors &
COMFYU_PID=$!

sleep 5  # 等待 ComfyUI 启动

# 启动 Web 服务（如果有）
echo "启动 Web 服务..."
cd /home/evynlau/桌面/ai_t2i_project
python app.py &
WEB_PID=$!

echo "✅ 全部启动完成"
echo "ComfyUI: http://127.0.0.1:8188"
echo "Web 服务: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待中断
wait
```

---

## 6. 定时任务配置

### 每天早上 8 点自动生成一张图

```python
import schedule, time, subprocess

def daily_generation():
    """每日图片生成"""
    prompt = "日出时分的宁静湖泊，薄雾，远景，电影感"
    subprocess.run([
        "python", "comfy_orchestrance.py",
        "workflows/zimage-turbo-t2i.json",
        prompt,
        f"daily_{time.strftime('%Y%m%d')}"
    ], check=True)

schedule.every().day.at("08:00").do(daily_generation)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Cron 方式

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天 8:00 执行）
0 8 * * * cd /home/evynlau/桌面/ai_t2i_project && python daily_gen.py >> /tmp/daily_gen.log 2>&1
```

---

## 7. 监控与告警

### 检查 ComfyUI 状态

```python
def check_comfyui_health():
    """检查 ComfyUI 是否正常运行"""
    try:
        r = requests.get(f"{COMFYU_URL}/system_stats", timeout=5)
        stats = r.json()
        vram_used = stats.get("vram_used", 0) / (1024**3)  # GB
        vram_total = stats.get("vram_total", 1) / (1024**3)
        
        print(f"显存: {vram_used:.1f}GB / {vram_total:.1f}GB")
        
        if vram_used / vram_total > 0.95:
            send_alert("显存即将耗尽！")
            return False
        return True
    except Exception as e:
        send_alert(f"ComfyUI 健康检查失败: {e}")
        return False
```

---

## 8. 常见问题排查

| 问题 | 检查点 |
|------|--------|
| 飞书消息发不出去 | 检查 AppID/AppSecret 是否正确 |
| 图片下载失败 | 确认 ComfyUI output 目录权限 |
| 批量任务中断 | 任务结果保存到 JSON，支持断点续传 |
| 显存不足 | 降低分辨率或批处理数量 |
| 模型加载失败 | 确认模型文件路径和完整性 |

---

## 本章小结

| 组件 | 作用 |
|------|------|
| comfy_orchestrance.py | ComfyUI 调度核心 |
| send_message_tool.py | 飞书通知 |
| start_all.sh | 一键启动 |
| story-batch-gen | 批量绘本生成 |
| schedule | 定时任务 |

---

## ⭐ 综合挑战

搭建一个完整的「**故事绘本生成流水线**」：

1. 准备一个 8-10 页的儿童故事（每页有场景描述）
2. 用 Z-image 批量生成每页插图
3. 将图片合成为 PDF 或视频
4. 配置每日自动执行

完成后，你将拥有一个**全自动的 AI 绘本生成系统**！🚀
