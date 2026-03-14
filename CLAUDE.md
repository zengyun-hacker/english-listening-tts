# Claude Code 工作规范

## Git 提交规范

每完成一个独立的功能点或 bug fix，主动执行 git commit，不需要等用户提醒。

- commit message 使用 Conventional Commits 格式（`feat` / `fix` / `refactor` / `chore` 等）
- 每个 commit 只做一件事，保持原子性
- commit message 末尾附上 co-author 信息：

```
Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>
```
