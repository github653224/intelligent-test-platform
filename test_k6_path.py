#!/usr/bin/env python3
"""测试k6路径查找"""
import os
import subprocess
import sys

# 添加backend到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def find_k6():
    """查找k6二进制文件"""
    common_paths = [
        "k6",  # 在PATH中
        "/opt/homebrew/bin/k6",  # macOS Homebrew (Apple Silicon)
        "/usr/local/bin/k6",  # macOS Homebrew (Intel) 或 Linux
        "/usr/bin/k6",  # Linux系统包管理器
    ]
    
    # 首先尝试which
    try:
        result = subprocess.run(
            ["which", "k6"],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            found_path = result.stdout.strip()
            if found_path and os.path.exists(found_path):
                print(f"✓ 在PATH中找到k6: {found_path}")
                return found_path
    except Exception as e:
        print(f"which命令失败: {e}")
    
    # 尝试常见路径
    for path in common_paths:
        if path == "k6":
            continue  # 已经尝试过which
        if os.path.exists(path) and os.access(path, os.X_OK):
            print(f"✓ 找到k6: {path}")
            return path
    
    print("✗ 未找到k6")
    return None

if __name__ == "__main__":
    k6_path = find_k6()
    if k6_path:
        # 测试k6版本
        try:
            result = subprocess.run(
                [k6_path, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"✓ k6版本信息:\n{result.stdout.strip()}")
            else:
                print(f"✗ k6版本检查失败: {result.stderr}")
        except Exception as e:
            print(f"✗ 执行k6版本检查失败: {e}")
    else:
        print("请确保k6已安装并在PATH中，或安装k6:")
        print("  macOS: brew install k6")
        print("  Linux: 参考 https://k6.io/docs/getting-started/installation/")

