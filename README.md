# Project Cognition Map

让项目 Agent 从你已经掌握的知识出发。

Project Cognition Map 是一个面向 Codex 的 Skill 与 Hook 集成。它在日常项目对话中维护一份简短的 Markdown，帮助 Agent 减少重复讲解、连接新旧知识，并把实验结果解释到你能够审阅的深度。

[快速开始](#快速开始) · [工作方式](#工作方式) · [认知地图](#认知地图) · [验证](#验证)

## 认知地图

地图只包含已掌握的知识。缩进表示掌握的深度。

```markdown
# 已掌握

## KV cache
- Prefill 与 decode 的分工
- 前缀复用
  - 相同文本在不同前文下的 KV 可能不同
  - 前缀命中与首 token 延迟的关系
```

用户可以直接阅读、修改这份文件。Agent 从相关节点继续解释。地图缺少某个细节时，它结合当前问题判断需要讲多深。

## 快速开始

要求 Python 3.10+、Git，以及支持 UserPromptSubmit 和 Stop 命令 Hook 的 Codex CLI。当前适配 Linux/macOS。

```sh
git clone https://github.com/Ben-cpy/BOOK-.git
cd BOOK-
python3 adapt-project-explanations/scripts/install.py --project /absolute/path/to/your/project
```

在目标项目的 Codex 中运行 `/hooks`，查看并信任新增的两个命令 Hook。随后照常讨论项目。

安装器会合并项目的 `.codex/hooks.json`，备份已有配置，并创建空的 `.know/map.md`。知识条目由日常对话逐步形成。请保留本仓库的本地路径，移动后重新运行安装器。

## 工作方式

1. **你提出项目问题。** UserPromptSubmit Hook 自动加载当前地图和 Skill。
2. **Agent 选择解释起点。** 用你已有的理解连接当前问题，需要时补一小段因果解释。
3. **Agent 根据自然对话更新认识。** 你用对一个概念、在同类问题上继续推进、或追问揭示原先理解仍有缺口时，它提出地图修改。
4. **Stop Hook 检查并保存。** 合格的修改写入地图。格式错误会返回给 Agent 修正，并发修改会要求重新合并。

理解判断由模型完成。代码负责触发、格式校验和写入一致性。单纯换话题的判断价值很低，模型会结合后续相关互动决定是否默认某部分已经理解。

## 示例

你问「开头变了，后面同样的文档为什么不能复用 KV？」Agent 先把因果链讲清楚：后面的 token 会看到不同的前文，其上下文 KV 可能随之改变，vLLM 标准 APC 因而把上游前缀也算入块身份。

后来你能据此判断哪些请求会命中，地图增加一条「相同文本在不同前文下的 KV 可能不同」。

接着你问「文档结尾只填半个块呢？」Agent 从块粒度继续解释。当后续互动表明这部分也理解了，地图在前缀复用下面增加「完整块与部分块的复用边界」。

[查看完整的正反案例](review/vllm-kv-oneshots.md)

## 验证

```sh
python3 adapt-project-explanations/scripts/know.py validate \
  adapt-project-explanations/references/map.example.md
python3 -m unittest discover -s adapt-project-explanations/tests -v
```

自动检查覆盖地图语法、实际安装命令、Hook 输入输出、保存与清理、错误重试，以及同时进行的两轮对话之间的写入冲突。

当前集成已按 Codex 官方事件协议实现并做本地回放测试。真实 Codex 会话的运行结果仍取决于安装版本、Hook 信任状态及模型是否正确使用上下文。测试环境没有 Codex CLI 可执行文件。

## 文件与隐私

`.know/map.md` 是用户维护的认知树。临时候选仅在当前更新期间用于校验。对话原文不会被 Hook 保存。安装器将运行状态加入目标仓库的本地忽略规则。

[Skill 规则](adapt-project-explanations/SKILL.md) · [格式与 Hook 协议](adapt-project-explanations/references/map-format.md) · [Codex Hook 文档](https://learn.chatgpt.com/docs/hooks)
