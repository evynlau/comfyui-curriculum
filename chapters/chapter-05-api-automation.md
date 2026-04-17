# 第五章 · API 自动化

> 学会这章，你可以从 Python、飞书、终端、甚至定时任务触发 ComfyUI 生成。

---

## 1. ComfyUI API 基础

ComfyUI 内置 REST API，无需额外安装。

### 启动时启用 API

```bash
python main.py --enable-cors
```

> `--enable-cors` 允许跨域请求（从网页调用时需要）。

### 关键接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/prompt` | POST | 提交工作流 |
| `/history/{prompt_id}` | GET | 查询执行结果 |
| `/queue` | GET | 查看队列状态 |
| `/system_stats` | GET | 查看系统状态（显存等）|
| `/interrupt` | POST | 中断当前任务 |

---

## 2. 提交工作流

### 基本格式

```python
import requests

COMFYU_URL = "http://127.0.0.1:8188"

workflow = {
    "3": {
        "inputs": {"prompt": "a cute cat"},
        "class_type": "CLIPTextEncode"
    },
    "4": {
        "inputs": {"width": 512, "height": 512},
        "class_type": "Empty Latent Image"
    }
    # ... 更多节点
}

resp = requests.post(f"{COMFYU_URL}/prompt", json={"prompt": workflow})
print(resp.json())
# {"prompt_id": "abc123...", "number": 1}
```

### 返回值

- `prompt_id`：用于后续查询的 ID
- `number`：队列序号

---

## 3. 等待并获取结果

### 方法一：轮询

```python
import time, requests

def wait_for_result(prompt_id, poll_interval=3, max_wait=300):
    """轮询直到任务完成"""
    for _ in range(max_wait // poll_interval):
        time.sleep(poll_interval)
        r = requests.get(f"{COMFYU_URL}/history/{prompt_id}", timeout=10)
        h = r.json()
        
        if prompt_id in h:
            status = h[prompt_id].get("status", {}).get("status_str")
            print(f"Status: {status}")
            
            if status == "success":
                outputs = h[prompt_id].get("outputs", {})
                imgs = []
                for node_out in outputs.values():
                    imgs.extend([i["filename"] for i in node_out.get("images", [])])
                return imgs
            elif status == "failed":
                print("Error:", h[prompt_id].get("status", {}).get("errors"))
                return []
    
    print("Timeout!")
    return []

# 使用
imgs = wait_for_result("abc123...")
print(f"生成完成，共 {len(imgs)} 张图片")
```

### 方法二：WebSocket 实时推送

```python
import websocket, json, threading

def listen_on_prompt(prompt_id, callback):
    def on_message(ws, message):
        data = json.loads(message)
        if data.get("type") == "executing" and data["data"].get("node") is None:
            # 全部执行完毕
            callback("done")
    
    def on_error(ws, error):
        print(f"WebSocket error: {error}")
    
    ws = websocket.WebSocketApp(
        f"ws://127.0.0.1:8188/ws",
        on_message=on_message,
        on_error=on_error
    )
    t = threading.Thread(target=ws.run_forever)
    t.start()
    return ws
```

---

## 4. 完整示例：发送 Z-image 工作流

```python
import requests, json, time

COMFYU_URL = "http://127.0.0.1:8188"

# Z-image Turbo 工作流
WORKFLOW = {
    "57:30": {
        "inputs": {"clip_name": "qwen_3_4b.safetensors", "device": "default", "type": "lumina2"},
        "class_type": "CLIPLoader"
    },
    "57:27": {
        "inputs": {"text": "一只穿着宇航服的橘猫，漂浮在太空中", "clip": ["57:30", 0]},
        "class_type": "CLIPTextEncode"
    },
    "57:33": {
        "inputs": {"conditioning": ["57:27", 0]},
        "class_type": "ConditioningZeroOut"
    },
    "57:28": {
        "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"},
        "class_type": "UNETLoader"
    },
    "57:11": {
        "inputs": {"model": ["57:28", 0], "shift": 3.0},
        "class_type": "ModelSamplingAuraFlow"
    },
    "57:13": {
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        "class_type": "EmptySD3LatentImage"
    },
    "57:3": {
        "inputs": {
            "model": ["57:11", 0],
            "positive": ["57:27", 0],
            "negative": ["57:33", 0],
            "latent_image": ["57:13", 0],
            "seed": 9527000,
            "steps": 8,
            "cfg": 1.0,
            "sampler_name": "res_multistep",
            "scheduler": "simple",
            "denoise": 1.0
        },
        "class_type": "KSampler"
    },
    "57:29": {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader"
    },
    "57:8": {
        "inputs": {"samples": ["57:3", 0], "vae": ["57:29", 0]},
        "class_type": "VAEDecode"
    },
    "9": {
        "inputs": {"filename_prefix": "zimage_result", "images": ["57:8", 0]},
        "class_type": "SaveImage"
    }
}

def generate(prompt_text, seed=9527000, output_prefix="result"):
    """发送工作流并返回生成结果"""
    WORKFLOW["57:27"]["inputs"]["text"] = prompt_text
    WORKFLOW["57:3"]["inputs"]["seed"] = seed
    WORKFLOW["9"]["inputs"]["filename_prefix"] = output_prefix
    
    # 1. 提交
    resp = requests.post(f"{COMFYU_URL}/prompt", json={"prompt": WORKFLOW}, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]
    print(f"已提交 prompt_id: {prompt_id}")
    
    # 2. 轮询等待
    for _ in range(100):  # 最多等 300 秒
        time.sleep(3)
        h = requests.get(f"{COMFYU_URL}/history/{prompt_id}", timeout=10).json()
        if prompt_id in h:
            if h[prompt_id]["status"]["status_str"] == "success":
                imgs = []
                for node_out in h[prompt_id]["outputs"].values():
                    imgs.extend(node_out.get("images", []))
                return imgs
            elif h[prompt_id]["status"]["status_str"] == "failed":
                raise Exception(f"生成失败: {h[prompt_id]['status'].get('errors')}")
    
    raise TimeoutError("生成超时")

# 使用
imgs = generate("一只穿宇航服的橘猫在太空中漂浮")
print(f"生成成功: {[img['filename'] for img in imgs]}")
```

---

## 5. 图片获取与下载

### 获取图片 URL

```python
# 图片保存在 ComfyUI/output/ 目录
# URL 格式：
image_url = f"{COMFYU_URL}/view?filename={filename}"

# 或下载到本地
def download_image(filename, save_path):
    url = f"{COMFYU_URL}/view?filename={filename}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(resp.content)
    print(f"已保存: {save_path}")
```

### 查看输出目录

```python
import os

# ComfyUI 默认输出目录
output_dir = "/home/evynlau/work/ComfyUI/output"
# 或从 API 获取
r = requests.get(f"{COMFYU_URL}/system_stats", timeout=10)
print(r.json())
```

---

## 6. 批量生成

```python
import concurrent.futures

prompts = [
    "一只穿宇航服的橘猫",
    "赛博朋克风格的城市夜景",
    "水彩画风格的小镇风光",
    "一只可爱的柴犬在海边"
]

def generate_batch(prompts, max_workers=2):
    """并发生成多张图片"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate, prompt, seed=i*1000, output_prefix=f"batch_{i}"): prompt
            for i, prompt in enumerate(prompts)
        }
        results = {}
        for future in concurrent.futures.as_completed(futures):
            prompt = futures[future]
            try:
                results[prompt] = future.result()
            except Exception as e:
                results[prompt] = f"Error: {e}"
        return results

# 使用（最多同时跑 2 个）
results = generate_batch(prompts, max_workers=2)
for prompt, imgs in results.items():
    print(f"{prompt}: {imgs}")
```

---

## 7. 从外部系统调用

### 从飞书调用

```python
# 飞书 Bot 收到消息后，解析 prompt，调用 ComfyUI API
@app.route("/webhook", methods=["POST"])
def feishu_webhook():
    data = request.json
    text = data.get("text", "")
    
    # 提取 prompt（飞书消息格式）
    if "/生成" in text:
        prompt = text.replace("/生成", "").strip()
        imgs = generate(prompt)
        # 发送图片回飞书
        send_images_to_feishu(imgs)
    
    return {"code": 0}
```

### 从定时任务调用

```python
# 每小时自动生成一张图
import schedule, time

def job():
    prompts = ["科技感城市夜景", "自然风光", "抽象艺术"]
    prompt = random.choice(prompts)
    imgs = generate(prompt, seed=int(time.time()))
    send_to_feishu(imgs)

schedule.every().hour.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| `Connection refused` | 确认 ComfyUI 已启动：`python main.py` |
| 提交后 400 错误 | 工作流节点 ID 冲突或缺少必需字段 |
| 轮询超时 | 检查显存是否不足，或任务卡住 |
| 跨域问题 | 启动时加 `--enable-cors` |

---

## 课后练习

1. ✅ 编写脚本，通过 API 生成一张 Z-image 图片
2. ✅ 实现轮询等待 + 自动下载图片到本地
3. ⭐ 实现批量生成 4 张不同 prompt 的图片
4. ⭐⭐ 结合飞书 Webhook，实现「发消息 → 自动生成 → 发回图片」

---

## 本章小结

| 技能 | 关键接口 |
|------|----------|
| 提交工作流 | `POST /prompt` |
| 查询结果 | `GET /history/{prompt_id}` |
| 轮询等待 | 每 3 秒查一次 status |
| 下载图片 | `/view?filename=xxx` |
| 批量生成 | ThreadPoolExecutor 并发 |
