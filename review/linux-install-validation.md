# Linux 本地安装验证

日期：2026-11-09。

## 环境与范围

- Linux，Codex CLI 0.167.0。
- uv 管理的 CPython 3.12.11。
- 本地仓库：`/home/warou/chen/BOOK`，从远端 main 的 `d5192aa` 开始修改。
- 本次仅调整文档，未修改 Skill 规则或运行脚本。

工作区原有 `/home/warou/chen/workspace/BOOK` 为其他系统用户所有，当前用户无法写入或 fetch，因此另行克隆到上述可写目录，未更改原目录权限。

## 检查结果

| 检查 | 结果 |
| --- | --- |
| `uv run --no-project python -m unittest discover -s adapt-project-explanations/tests -v` | 36/36 通过 |
| `uv run --no-project python adapt-project-explanations/scripts/know.py validate adapt-project-explanations/references/map.example.md` | 校验通过 |
| `uv run --no-project python adapt-project-explanations/scripts/install.py --global` | 安装成功 |
| 全局 hooks.json 中两个 Project Cognition Map 处理器 | 各一个，指向安装后的运行脚本 |
| 已安装规则、脚本、references 与仓库源文件逐字节比较 | 一致 |
| 临时 Git 项目中执行实际注册的 UserPromptSubmit 命令 | 创建空图并输出 Skill、地图上下文 |
| 写入合成候选后执行实际注册的 Stop 命令 | 保存正确，清理候选 |
| `git diff --check` | 通过 |

全局运行位置是 `/home/warou/.codex/cognition-runtime/adapt-project-explanations/`，配置位于 `/home/warou/.codex/hooks.json`。安装命令记录 uv 选择的持久解释器路径，无需每轮启动 uv。测试项目使用临时目录，验证结束后清理；未向实际项目写入示例知识。

## 解释边界

本轮调用真实的已安装 Hook 命令，使用合成事件与候选验证加载和保存链路；未启动真实模型会话，未证明 Linux 上的自然对话理解效果，也未验证 macOS。现有 Windows 真实会话证据见[原报告](codex-live-validation.md)。

安装不会替用户授予 Hook 信任。下一次启动目标项目的 Codex 会话时，需在启动提示或 `/hooks` 中审阅并信任两个处理器，确认 Active，才能验证 Codex UI 层的实际启用状态。
