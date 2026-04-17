#!/usr/bin/env python3
"""
ComfyUI 图像生成调度器
用法:
    python send_workflow.py <workflow.json> <prompt> [seed] [output_prefix]
示例:
    python send_workflow.py zimage-turbo-t2i.json "一只穿宇航服的橘猫"
"""

import sys
import json
import time
import requests
from pathlib import Path

COMFYU_URL = "http://127.0.0.1:8188"


def load_workflow(json_path: str) -> dict:
    """加载工作流 JSON 文件"""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def set_workflow_prompt(workflow: dict, prompt_text: str, seed: int = None) -> dict:
    """修改工作流中的提示词和种子"""
    for node_id, node in workflow.items():
        # 设置 CLIPTextEncode 的 text
        if node.get("class_type") == "CLIPTextEncode":
            node["inputs"]["text"] = prompt_text
        # 设置 KSampler 的 seed
        if seed is not None and node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = seed
        # 设置 SaveImage 的 prefix
        if node.get("class_type") == "SaveImage":
            if "filename_prefix" in node["inputs"]:
                prefix = prompt_text[:20].replace(" ", "_").replace(",", "")
                node["inputs"]["filename_prefix"] = f"api_{prefix}"
    return workflow


def send_prompt(workflow: dict) -> str:
    """提交工作流到 ComfyUI，返回 prompt_id"""
    resp = requests.post(
        f"{COMFYU_URL}/prompt",
        json={"prompt": workflow},
        timeout=30
    )
    resp.raise_for_status()
    result = resp.json()
    return result["prompt_id"]


def get_history(prompt_id: str) -> dict:
    """获取任务历史"""
    resp = requests.get(f"{COMFYU_URL}/history/{prompt_id}", timeout=10)
    return resp.json()


def wait_for_completion(prompt_id: str, poll_interval: int = 3, max_wait: int = 300) -> list:
    """
    轮询等待任务完成，返回图片文件列表
    """
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        h = get_history(prompt_id)
        if prompt_id not in h:
            continue

        status_str = h[prompt_id]["status"]["status_str"]
        print(f"  [{elapsed}s] status: {status_str}")

        if status_str == "success":
            imgs = []
            for node_output in h[prompt_id]["outputs"].values():
                imgs.extend(node_output.get("images", []))
            return imgs

        if status_str == "failed":
            errors = h[prompt_id]["status"].get("errors", [])
            raise Exception(f"任务失败: {errors}")

    raise TimeoutError(f"等待超时（{max_wait}s）")


def download_image(filename: str, save_dir: str = "./downloads") -> str:
    """下载图片到本地目录"""
    Path(save_dir).mkdir(exist_ok=True)
    save_path = Path(save_dir) / filename

    url = f"{COMFYU_URL}/view?filename={filename}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with open(save_path, "wb") as f:
        f.write(resp.content)

    return str(save_path)


def generate(prompt_text: str, workflow_path: str, seed: int = None, download: bool = True):
    """
    完整流程：加载工作流 → 修改提示词 → 提交 → 等待 → 返回结果
    """
    print(f"📝 Prompt: {prompt_text}")
    if seed:
        print(f"🎲 Seed: {seed}")

    # 1. 加载
    workflow = load_workflow(workflow_path)
    workflow = set_workflow_prompt(workflow, prompt_text, seed)

    # 2. 提交
    print("🚀 提交到 ComfyUI...")
    prompt_id = send_prompt(workflow)
    print(f"   prompt_id: {prompt_id}")

    # 3. 等待
    print("⏳ 等待生成...")
    imgs = wait_for_completion(prompt_id)
    print(f"✅ 完成！共 {len(imgs)} 张图片")

    # 4. 下载（可选）
    if download:
        print("📥 下载图片...")
        saved = []
        for img in imgs:
            path = download_image(img["filename"])
            saved.append(path)
            print(f"   → {path}")
        return saved

    return imgs


def main():
    if len(sys.argv) < 3:
        print("用法: python send_workflow.py <workflow.json> <prompt> [seed] [output_prefix]")
        sys.exit(1)

    workflow_path = sys.argv[1]
    prompt = sys.argv[2]
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else None

    try:
        results = generate(prompt, workflow_path, seed)
        print("\n🎉 全部完成！")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
