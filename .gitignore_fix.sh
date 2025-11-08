#!/bin/bash
# 从 Git 中移除应该被忽略的文件

echo "正在从 Git 中移除 node_modules..."
git rm -r --cached frontend/node_modules/ 2>/dev/null || true

echo "正在从 Git 中移除 __pycache__..."
find . -type d -name "__pycache__" -exec git rm -r --cached {} + 2>/dev/null || true

echo "正在从 Git 中移除 .pyc 文件..."
find . -name "*.pyc" -exec git rm --cached {} + 2>/dev/null || true

echo "正在从 Git 中移除 build 目录..."
git rm -r --cached frontend/build/ 2>/dev/null || true

echo "完成！现在运行 'git status' 查看状态"
