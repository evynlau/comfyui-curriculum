#!/usr/bin/env python3
"""
批量故事绘本生成器
从 scenes.json 读取场景列表，批量生成图片
"""

import json
import time
import sys
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

COMFYU_URL = "http://127.0.0.1:8188"
WORKFLOW_PATH = "zimage-turbo-t2i.json"


def load_scenes(config_path: str = "scenes.json") -> list:
    """加载场景配置"""
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)["scenes"]


def load_workflow(path: str = WORKFLOW_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_single(scene: dict, idx: int) -> dict:
    """生成单个场景，返回结果"""
    name = scene["name"]
    prompt = scene["prompt"]
    print(f"[{idx+1}] 生成: {name}")

    workflow = load_workflow()
    workflow["57:27"]["inputs"]["text"] = prompt
    workflow["57:3"]["inputs"]["seed"] = 9527000 + idx

    # 提交
    resp = requests.post(f"{COMFYU_URL}/prompt", json={"prompt": workflow}, timeout=30)
    resp.raise_for_status()
    prompt_id = resp.json()["prompt_id"]

    # 轮询
    for _ in range(200):
        time.sleep(3)
        h = requests.get(f"{COMFYU_URL}/history/{prompt_id}", timeout=10).json()
        if prompt_id in h and h[prompt_id]["status"]["status_str"] == "success":
            imgs = []
            for out in h[prompt_id]["outputs"].values():
                imgs.extend(out.get("images", []))
            filenames = [img["filename"] for img in imgs]
            print(f"  ✅ {name}: {filenames}")
            return {"scene": name, "prompt": prompt, "images": filenames, "status": "success"}

    print(f"  ❌ {name}: 超时")
    return {"scene": name, "prompt": prompt, "images": [], "status": "timeout"}


def batch_generate(config_path: str = "scenes.json", max_workers: int = 2):
    """
    批量生成所有场景
    max_workers: 同时并发的 ComfyUI 任务数（建议 ≤ 2）
    """
    scenes = load_scenes(config_path)
    print(f"📚 共 {len(scenes)} 个场景，开始批量生成（并发数: {max_workers}）\n")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_single, scene, i): scene
            for i, scene in enumerate(scenes)
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # 保存结果
    output_path = "generation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(scenes),
            "completed": sum(1 for r in results if r["status"] == "success"),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📊 完成！成功 {sum(1 for r in results if r['status'] == 'success')}/{len(scenes)}")
    print(f"📁 结果已保存: {output_path}")
    return results


# scenes.json 格式示例
SCENES_EXAMPLE = {
    "scenes": [
        {
            "name": "scene01_start",
            "prompt": "山间日出，薄雾环绕，远景，温暖光线，电影感"
        },
        {
            "name": "scene02_discovery",
            "prompt": "一位探险家在雪地中发现一只白狐，特写，梦幻氛围"
        },
        {
            "name": "scene03_action",
            "prompt": "白狐在雪地奔跑，雪花飞溅，动感模糊，电影感"
        },
        {
            "name": "scene04_ending",
            "prompt": "夕阳下白狐回头望向探险家，温暖色调，大远景"
        }
    ]
}


if __name__ == "__main__":
    # 如果没有 scenes.json，创建一个示例
    if not Path("scenes.json").exists():
        with open("scenes.json", "w", encoding="utf-8") as f:
            json.dump(SCENES_EXAMPLE, f, indent=2, ensure_ascii=False)
        print("✅ 已创建 scenes.json 示例文件，请编辑后重新运行")

    batch_generate()
