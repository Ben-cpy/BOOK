# 使用指南

[返回 README](../README.md)

## 安装位置与项目边界

全局安装命令：

```sh
python3 adapt-project-explanations/scripts/install.py --global
```

安装器将 Skill、scripts 和 references 复制到 `<CODEX_HOME>/cognition-runtime/adapt-project-explanations/`，在 `<CODEX_HOME>/hooks.json` 合并 `UserPromptSubmit`、`Stop` 两个触发器。`CODEX_HOME` 默认是 `~/.codex`。复制后的运行文件不依赖克隆仓库的位置。

Hook 已经在每轮注入完整规则，因此运行副本放在 Skill 自动发现目录之外。仅把 `SKILL.md` 复制到 skills 目录不能代替 Hook 安装。

Git 仓库与 worktree 使用各自根目录下的 `.know/map.md`；仓库内的子目录共享这份地图。独立嵌套仓库使用自己的地图。

非 Git 项目会寻找最近的已有地图，否则将当前目录视为项目根；首次应从预期根目录启动。程序无法从一个尚无地图的子目录推断上层项目边界。裸用户主目录和文件系统根目录不会成为全局记忆存储。

运行文件会加入项目本地 Git 忽略规则。`.know/map.md` 使用 UTF-8、LF 换行，每行是知识标签，可以直接查看和纠正；[完整格式约束](../adapt-project-explanations/references/map-format.md)由校验器执行。

## 单项目安装

```sh
python3 adapt-project-explanations/scripts/install.py --project /absolute/path/to/project
```

此模式创建项目空地图并修改项目 `.codex/hooks.json`，引用克隆仓库中的脚本。移动仓库后需重新安装。当前版本的全局和项目 Hook 同时启用时，每轮只注入一次；旧版单项目安装应先重跑安装器更新。

## 更新与备份

在 BOOK 克隆仓库执行：

```sh
git pull --ff-only
python3 adapt-project-explanations/scripts/install.py --global
```

安装器保留其他 Hook，按名称替换自己的两个处理器；不会清空项目地图。已有配置首次备份为同目录的 `hooks.before-cognition.json`；已有全局运行副本首次备份为 `<CODEX_HOME>/cognition-skill.before-install/`。这些是首次备份，不是每次更新的历史快照。

Hook 定义变化后，在新 Codex 会话的 `/hooks` 中重新检查信任。安装器不代替用户授予信任。

## 停用与移除

在 `/hooks` 中停用两个 Project Cognition Map Hook，即可停止自动加载与保存。

如需完全移除，先结束使用这些 Hook 的会话，备份当前 `hooks.json`，只移除 `UserPromptSubmit` 和 `Stop` 中 `statusMessage` 为 `Project Cognition Map` 的处理器；保留同组的其他处理器。单项目安装需检查项目 `.codex/hooks.json`，全局安装需检查 `<CODEX_HOME>/hooks.json`。

移除对应配置后可删除全局 `cognition-runtime/adapt-project-explanations/`。项目地图可以保留；删除 `.know/` 会丢失该项目的理解记录，仍启用的 Hook 会在下一次输入时重新创建空图。不要用旧备份整体覆盖后来增加了其他 Hook 的配置。

## 故障排查

| 现象 | 检查与处理 |
| --- | --- |
| 没有 `.know/map.md` | 用新会话检查 `/hooks` 中两个 Hook 是否 Active；确认启动的是目标项目、Python 3.9+ 可执行、安装路径存在 |
| 地图存在但一直为空 | 检查写入权限；仅问问题或听完解释不要求更新，需后续理解证据 |
| 非 Git 项目地图出现在子目录 | 从预期项目根首次启动；先审阅已有地图，再决定是否迁移，避免混入其他项目知识 |
| 报地图格式错误 | 按[协议](../adapt-project-explanations/references/map-format.md)纠正 UTF-8、标题、缩进和标签；也可用下方命令校验 |
| 更新后不再触发 | 检查 Python 路径与 Hook 信任；单项目模式移动仓库后重装 |
| 中断后留下 `pending/` | 同会话下次输入会清理旧候选；永不恢复的会话，在确认结束后可删除其临时目录 |

校验地图：

```sh
python3 adapt-project-explanations/scripts/know.py validate /absolute/path/to/project/.know/map.md
```

## 限制与隐私

- 每个项目默认由同一位用户使用，尚无多人身份隔离。
- 理解判断由模型完成。正确表述可能只是照抄，也可能漏记或记得过宽；格式校验不能证明理解，长期准确率尚未建立。
- 正常回合不播报维护；格式修复或并发冲突可能触发一次续答或重复回答。
- 锁协调遵守协议的写入，不能完全防止外部编辑器在保存瞬间写入造成竞争。
- 生产 Hook 不保存对话原文；会保存地图、候选和基线快照，地图作为上下文发送给所配置的模型服务。Codex 自身管理其会话记录。
- 永不恢复的中断会话可能留下临时目录，不会自动将其候选提交为正式地图。
- 真实会话测试驱动额外保存合成对话证据，运行前应检查脚本及输出路径。

## 开发验证

脚本只依赖 Python 标准库。可使用 uv：

```sh
uv run --no-project python -m unittest discover -s adapt-project-explanations/tests -v
uv run --no-project python adapt-project-explanations/scripts/know.py validate adapt-project-explanations/references/map.example.md
```

可选的真实会话测试使用当前 Codex 配置和模型额度，在临时 Git 项目输出证据。先审阅 Hook 代码：此测试驱动对单次调用绕过 Hook 信任，日常使用仍通过 `/hooks` 审阅。

```sh
uv run --no-project python adapt-project-explanations/tests/live_codex.py --scenario adapt-project-explanations/tests/scenarios/kv-cache.json
```

驱动退出成功不等于语义检查通过，还需检查回答、地图和 `hook-events.jsonl`。已有[真实会话报告](../review/codex-live-validation.md)与[全局安装报告](../review/global-install-validation.md)保留各自验证环境与范围。
