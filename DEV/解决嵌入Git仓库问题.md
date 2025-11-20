# 解决嵌入Git仓库问题

## 问题描述

执行 `git add .` 时出现警告：
```
warning: adding embedded git repository: ApolloOracle
```

这是因为项目目录中存在一个 `ApolloOracle` 子目录，它包含自己的 `.git` 目录，Git将其识别为嵌入的仓库。

## 解决方案

### 方法1：删除ApolloOracle目录（推荐）

如果 `ApolloOracle` 目录只包含 LICENSE 文件，可以按以下步骤处理：

```bash
# 1. 从Git缓存中移除ApolloOracle
git rm --cached ApolloOracle

# 2. 如果ApolloOracle目录中有LICENSE文件，先复制到项目根目录
# Windows PowerShell
if (Test-Path ApolloOracle\LICENSE) {
    Copy-Item ApolloOracle\LICENSE . -Force
}

# 3. 删除ApolloOracle目录（包括其.git目录）
# Windows PowerShell
Remove-Item -Recurse -Force ApolloOracle

# 或者手动删除：
# - 在文件管理器中删除 ApolloOracle 文件夹
# - 确保删除整个文件夹，包括隐藏的 .git 目录

# 4. 重新添加所有文件
git add .

# 5. 检查状态
git status
```

### 方法2：移除ApolloOracle中的.git目录

如果想保留ApolloOracle目录的内容，但将其作为普通目录：

```bash
# 1. 从Git缓存中移除
git rm --cached ApolloOracle

# 2. 删除ApolloOracle中的.git目录
# Windows PowerShell
Remove-Item -Recurse -Force ApolloOracle\.git

# 3. 重新添加
git add ApolloOracle
```

### 方法3：将ApolloOracle作为子模块（不推荐）

如果确实需要将其作为子模块：

```bash
# 1. 从Git缓存中移除
git rm --cached ApolloOracle

# 2. 添加为子模块
git submodule add https://github.com/weijianfa/ApolloOracle.git ApolloOracle
```

**注意**：对于本项目，不推荐使用子模块，因为ApolloOracle目录应该就是项目本身。

---

## 推荐操作步骤

根据当前情况，推荐执行以下步骤：

```bash
# 步骤1：从Git缓存中移除ApolloOracle
git rm --cached ApolloOracle

# 步骤2：检查ApolloOracle目录内容
# 如果只有LICENSE文件，可以复制到根目录后删除该目录

# 步骤3：删除ApolloOracle目录（包括.git）
# Windows PowerShell
Remove-Item -Recurse -Force ApolloOracle

# 步骤4：重新添加所有文件
git add .

# 步骤5：检查状态，确认没有警告
git status
```

---

## 验证

执行 `git add .` 后，不应该再看到嵌入仓库的警告。

如果仍有问题，检查是否还有其他包含 `.git` 目录的子目录：

```bash
# Windows PowerShell
Get-ChildItem -Recurse -Directory -Filter ".git" | Select-Object FullName
```

---

## 注意事项

1. **不要删除项目根目录的 `.git`**：只删除 `ApolloOracle/.git`
2. **备份重要文件**：删除前确保已备份LICENSE等文件
3. **检查.gitignore**：确保 `.gitignore` 正确配置，排除不需要的文件

