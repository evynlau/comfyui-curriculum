#!/usr/bin/env python3
"""
轮询脚本 - 监控 ComfyUI 队列状态并下载完成的结果
用法:
    python poll_and_save.py <prompt_id> [output_dir]
"""

import sys
import time
import requests
from pathlib import Path

COMFYU_URL = "http://127.0.0.1:8188"


def get_status(prompt_id: str) -> dict:
    """获取任务状态"""
    resp = requests.get(f"{COMFYU_URL}/history/{prompt_id}", timeout=10)
    return resp.json()


def get_queue() -> list:
    """获取当前队列"""
    resp = requests.get(f"{COMFYU_URL}/queue", timeout=10)
    return resp.json().get("queue_running", [])


def download_image(filename: str, save_dir: str = "./downloads") -> str:
    """下载单张图片"""
    Path(save_dir).mkdir(exist_ok=True)
    save_path = Path(save_dir) / filename

    url = f"{COMFYU_URL}/view?filename={filename}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    with open(save_path, "wb") as f:
        f.write(resp.content)
    return str(save_path)


def wait_and_download(prompt_id: str, output_dir: str = "./downloads", poll_interval: int = 3):
    """等待任务完成并下载所有图片"""
    print(f"🔍 监控 prompt_id: {prompt_id}")
    print(f"📁 保存到: {output_dir}")
    print()

    last_status = None
    while True:
        h = get_status(prompt_id)

        if prompt_id not in h:
            print(f"⏳ 等待中... (队列: {len(get_queue())} 个任务运行中)")
            time.sleep(poll_interval)
            continue

        status = h[prompt_id]["status"]["status_str"]

        if status != last_status:
            print(f"📌 状态: {status}")
            last_status = status

        if status == "success":
            print("\n✅ 生成成功！")
            outputs = h[prompt_id].get("outputs", {})

            for node_id, node_out in outputs.items():
                imgs = node_out.get("images", [])
                for img in imgs:
                    path = download_image(img["filename"], output_dir)
                    print(f"  📥 {img['filename']} → {path}")

            return outputs

        if status == "failed":
            print("\n❌ 生成失败！")
            errors = h[prompt_id]["status"].get("errors", [])
            print(f"   错误: {errors}")
            return None

        time.sleep(poll_interval)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python poll_and_save.py <prompt_id> [output_dir]")
        print()
        print("示例:")
        print("  python poll_and_save.py abc123def456")
        print("  python poll_and_save.py abc123def456 ./my_images")
        sys.exit(1)

    prompt_id = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./downloads"

    try:
        wait_and_download(prompt_id, output_dir)
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
