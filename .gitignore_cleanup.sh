#!/bin/bash
# Git 清理脚本 - 从 Git 跟踪中移除应该被忽略的文件

set -e

echo "🔍 检查需要清理的文件..."

# 统计要清理的文件数量
PYCACHE_COUNT=$(git ls-files | grep "__pycache__" | wc -l | tr -d ' ')
PYC_COUNT=$(git ls-files | grep "\.pyc$" | wc -l | tr -d ' ')
NODE_MODULES_COUNT=$(git ls-files | grep "node_modules" | wc -l | tr -d ' ')
BUILD_COUNT=$(git ls-files | grep "frontend/build" | wc -l | tr -d ' ')

echo "发现以下需要清理的文件："
echo "  - __pycache__ 目录: $PYCACHE_COUNT 个文件"
echo "  - .pyc 文件: $PYC_COUNT 个"
echo "  - node_modules: $NODE_MODULES_COUNT 个文件"
echo "  - frontend/build: $BUILD_COUNT 个文件"
echo ""

if [ "$PYCACHE_COUNT" -eq 0 ] && [ "$PYC_COUNT" -eq 0 ] && [ "$NODE_MODULES_COUNT" -eq 0 ] && [ "$BUILD_COUNT" -eq 0 ]; then
    echo "✅ 没有需要清理的文件！"
    exit 0
fi

read -p "是否继续清理？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 1
fi

echo ""
echo "🧹 开始清理..."

# 1. 清理所有 __pycache__ 目录
if [ "$PYCACHE_COUNT" -gt 0 ]; then
    echo "  清理 __pycache__ 目录..."
    git ls-files | grep "__pycache__" | xargs -I {} git rm --cached -r {} 2>/dev/null || true
fi

# 2. 清理所有 .pyc 文件
if [ "$PYC_COUNT" -gt 0 ]; then
    echo "  清理 .pyc 文件..."
    git ls-files | grep "\.pyc$" | xargs git rm --cached 2>/dev/null || true
fi

# 3. 清理 node_modules
if [ "$NODE_MODULES_COUNT" -gt 0 ]; then
    echo "  清理 node_modules..."
    git ls-files | grep "node_modules" | xargs git rm --cached 2>/dev/null || true
fi

# 4. 清理 build 目录
if [ "$BUILD_COUNT" -gt 0 ]; then
    echo "  清理 frontend/build..."
    git ls-files | grep "frontend/build" | xargs git rm --cached 2>/dev/null || true
fi

echo ""
echo "✅ 清理完成！"
echo ""
echo "📋 下一步："
echo "  1. 运行 'git status' 查看更改"
echo "  2. 运行 'git commit -m \"Remove ignored files from Git tracking\"' 提交更改"
echo "  3. 运行 'git push' 推送到远程仓库（如果需要）"
echo ""

