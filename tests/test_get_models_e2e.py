import asyncio
import json
import os
import sys
import types
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
if "websockets" not in sys.modules:
    sys.modules["websockets"] = types.ModuleType("websockets")

from comfy_library.client import ComfyUIClient

COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFYUI_TEST_FOLDER = os.getenv("COMFYUI_TEST_FOLDER", "checkpoints")


async def _live_get_models(folder=None, filter_name=False):
    async with ComfyUIClient(COMFYUI_BASE_URL) as client:
        return await client.get_models(folder=folder, filter_name=filter_name)


async def _live_get_model_names(folder=None):
    async with ComfyUIClient(COMFYUI_BASE_URL) as client:
        return await client.get_models(folder=folder, filter_name=True)


def _extract_folder_name(groups):
    if not isinstance(groups, list) or not groups:
        return None
    first = groups[0]
    if isinstance(first, dict):
        return first.get("name")
    if isinstance(first, str):
        return first
    return None


def test_get_models_live_groups():
    try:
        groups = asyncio.run(_live_get_models())
    except Exception as e:
        pytest.skip(f"ComfyUI 不可访问，跳过真实连通性测试: {e}")
    print("[live-test] get_models() =>")
    print(json.dumps(groups, ensure_ascii=False, indent=2))


def test_get_models_live_folder():
    try:
        groups = asyncio.run(_live_get_models())
    except Exception as e:
        pytest.skip(f"ComfyUI 不可访问，跳过真实连通性测试: {e}")
    folder = _extract_folder_name(groups) or COMFYUI_TEST_FOLDER
    models = asyncio.run(_live_get_models(folder=folder))
    print(f"[live-test] get_models(folder={folder}) =>")
    print(json.dumps(models, ensure_ascii=False, indent=2))


def test_get_models_live_groups_filter_name():
    try:
        groups = asyncio.run(_live_get_models())
    except Exception as e:
        pytest.skip(f"ComfyUI 不可访问，跳过真实连通性测试: {e}")
    groups = asyncio.run(_live_get_models(filter_name=True))
    print(f"[live-test] get_models(filter_name=True) =>")
    print(json.dumps(groups, ensure_ascii=False, indent=2))

def test_get_models_live_filter_name():
    try:
        groups = asyncio.run(_live_get_models())
    except Exception as e:
        pytest.skip(f"ComfyUI 不可访问，跳过真实连通性测试: {e}")
    folder = _extract_folder_name(groups) or COMFYUI_TEST_FOLDER
    names = asyncio.run(_live_get_model_names(folder=folder))
    print(f"[live-test] get_models(folder={folder}, filter_name=True) =>")
    print(json.dumps(names, ensure_ascii=False, indent=2))

