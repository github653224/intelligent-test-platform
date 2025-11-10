# Git 推送问题快速参考

## 🚨 常见问题速查

### 问题 1：node_modules 被跟踪

**症状**：`git status` 显示 `node_modules/` 被修改

**解决**：
```bash
git rm -r --cached node_modules/
git commit -m "Remove node_modules from tracking"
```

### 问题 2：GitHub 拒绝推送 - 文件超过 100MB

**症状**：
```
remote: error: File ... is 108.71 MB; this exceeds GitHub's file size limit
```

**解决**：
```bash
# 方法 1：从历史中移除（如果已提交）
git filter-branch --force --index-filter \
  'git rm -r --cached --ignore-unmatch node_modules' \
  --prune-empty --tag-name-filter cat -- --all

# 清理
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# 强制推送
git push -u origin master --force
```

**或方法 2：完全重新开始（新仓库推荐）**
```bash
rm -rf .git
git init
git add .
git commit -m "Initial commit"
git remote add origin <url>
git push -u origin master --force
```

### 问题 3：.gitignore 不生效

**症状**：添加了 `.gitignore` 规则，但文件仍被跟踪

**解决**：
```bash
# 从跟踪中移除（不删除本地文件）
git rm --cached <file>
git commit -m "Remove from tracking"
```

## 📋 推送前检查清单

```bash
# 1. 检查敏感信息
grep -r "sk-\|password" . --exclude-dir=node_modules --exclude-dir=.git

# 2. 检查大文件
find . -type f -size +10M -not -path "./.git/*" -not -path "./node_modules/*"

# 3. 检查 .env
git status | grep ".env"

# 4. 检查 Git 历史中的大文件
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ && $3 > 100000000'
```

## ✅ 标准 .gitignore 配置

```gitignore
# Node.js
node_modules/
**/node_modules/
npm-debug.log*
**/.cache/

# Python
__pycache__/
**/__pycache__/
*.pyc
venv/
env/

# 构建产物
build/
dist/
*.map

# 环境变量
.env
.env.local

# 日志
*.log
logs/
```

## 🎯 最佳实践

1. ✅ **项目开始就创建 .gitignore**
2. ✅ **使用 .env.example 而不是 .env**
3. ✅ **推送前检查敏感信息和大文件**
4. ✅ **不要提交 node_modules、__pycache__、build/**

## 📚 详细文档

查看 [Git和GitHub推送问题解决方案总结.md](Git和GitHub推送问题解决方案总结.md) 获取完整文档。

