# Security Policy

## Supported version

当前 public alpha 只维护默认分支上的最新版本。

## Reporting a vulnerability

请不要为路径逃逸、任意文件覆盖、符号链接绕过或敏感信息泄露直接创建公开 issue。
请使用 GitHub 仓库的 **Security → Report a vulnerability** 私下提交：

- 受影响版本或 commit；
- 最小复现步骤；
- 可能读写到的路径范围；
- 建议修复（如有）。

在修复和披露时间达成一致前，请不要公开利用细节。

## Security model

本项目默认本地运行，不发送文档到网络。安装和迁移先 dry-run，路径写入被限制在
明确的项目根内，符号链接逃逸和不同文件的静默覆盖会被拒绝。
