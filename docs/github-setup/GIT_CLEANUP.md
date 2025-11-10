# Git 清理指南

## ⚠️ 问题说明

如果 `node_modules`、`__pycache__` 或 `build/` 目录中的文件显示为已修改或被跟踪，说明它们之前已经被提交到 Git 了。需要从 Git 历史中移除这些文件。

## 🔧 解决方案

### 方法一：从 Git 中移除（推荐）

运行以下命令从 Git 跟踪中移除这些文件（不会删除本地文件）：

```bash
# 1. 移除 node_modules
git rm -r --cached frontend/node_modules/

# 2. 移除所有 __pycache__ 目录
find . -type d -name "__pycache__" -exec git rm -r --cached {} +

# 3. 移除所有 .pyc 文件
find . -name "*.pyc" -exec git rm --cached {} +

# 4. 移除 build 目录
git rm -r --cached frontend/build/

# 5. 提交更改
git commit -m "Remove ignored files from Git tracking"
```

### 方法二：使用提供的脚本

```bash
# 运行清理脚本
./.gitignore_fix.sh

# 然后提交
git commit -m "Remove ignored files from Git tracking"
```

### 方法三：一次性清理所有

```bash
# 从 Git 中移除所有应该被忽略的文件
git rm -r --cached .
git add .
git commit -m "Fix .gitignore and remove tracked ignored files"
```

## ✅ 验证

清理后，运行以下命令验证：

```bash
# 检查是否还有不应该跟踪的文件
git ls-files | grep -E "(node_modules|__pycache__|\.pyc|build/)"

# 应该没有输出，或者只有必要的文件

# 检查大文件
find . -type f -size +10M -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./frontend/build/*"

# 应该只看到 node_modules 和 build 中的文件（这些会被忽略）
```

## 📝 注意事项

1. **不会删除本地文件**：`git rm --cached` 只会从 Git 跟踪中移除，不会删除本地文件
2. **提交前检查**：运行 `git status` 确认要提交的文件
3. **如果文件已推送**：如果这些文件已经推送到远程仓库，需要：
   ```bash
   git push origin main --force
   ```
   ⚠️ **注意**：强制推送会覆盖远程历史，确保团队其他成员知道

## 🎯 推送前最终检查

```bash
# 1. 检查要提交的文件
git status

# 2. 确认没有大文件
git ls-files | xargs ls -lh | awk '{if ($5 > 10000000) print $5, $9}'

# 3. 确认没有敏感信息
grep -r "sk-" . --exclude-dir=node_modules --exclude-dir=.git | grep -v ".example"

# 4. 确认 .env 不会被提交
git status | grep ".env"

# 5. 查看将要提交的文件列表
git diff --cached --name-only
```

## 🚀 安全推送

确认无误后：

```bash
# 添加所有更改
git add .

# 提交
git commit -m "Initial commit: AI智能测试平台"

# 推送到 GitHub
git push -u origin main
```

