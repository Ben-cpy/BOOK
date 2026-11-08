# Project Cognition Map

让项目 Agent 记住：你已经理解到哪里，下次应该从哪里接着讲。

当你会看实验结果，却还不懂某个机制时，AI 容易从头重复定义，或直接跳到你接不上的结论。这个 Skill 维护项目内的知识边界，让回答省掉已经会的部分，把解释用在当前缺少的因果连接上。

**当前定位：真实 Codex 链路已跑通的可试用版本。** 它从自然对话中作出可纠正的理解判断，仍需真实用户验证解释深度是否合适。

[验证报告](review/codex-live-validation.md) · [安装](#安装一次各项目独立生效) · [记忆文件](#记忆文件是什么样) · [Skill 规则](adapt-project-explanations/SKILL.md)

## 安装一次，各项目独立生效

全局安装的是 Skill 和 Hook，记忆始终放在项目目录里：

```text
~/.codex/cognition-runtime/adapt-project-explanations/  ← 全局规则与脚本
~/.codex/hooks.json                                    ← 全局触发器

/work/proj-a/.know/map.md                    ← 只记录 A 项目知识边界
/work/proj-b/.know/map.md                    ← 只记录 B 项目知识边界
```

不需要给每个项目重复安装。第一次在项目中发消息时，Hook 自动创建该项目的空地图。Git 项目使用仓库根目录，子目录沿用同一份地图；另一个 Git 仓库或 worktree 使用自己的文件。非 Git 项目应先从项目根启动，之后子目录沿用最近的已有地图。非 Git 首次从子目录启动时，程序无法猜出上层项目边界，会把该目录作为项目根。

需要 Git、Python **3.9+** 和支持 `UserPromptSubmit` / `Stop` 的 Codex CLI。本轮实测 **Windows、Codex CLI 0.164.0、Python 3.9.13、配置模型 gpt-6-astra**；其他版本及 Linux/macOS 本轮未实测。

```sh
git clone https://github.com/Ben-cpy/BOOK.git
cd BOOK
```

Windows（可用 `py -0p` 查看 Python，并换用更高版本）：

```powershell
py -3.9 -X utf8 adapt-project-explanations/scripts/install.py --global
codex -C "C:\path\to\your-project"
```

Linux/macOS：

```sh
python3 adapt-project-explanations/scripts/install.py --global
codex -C /work/proj-a
```

在启动提示或 `/hooks` 中审阅并信任 **UserPromptSubmit、Stop 两个 Project Cognition Map Hook**，检查均为 Active。随后正常讨论项目即可。若 Codex 要求信任当前项目，也需完成项目授权。安装器不替用户授予信任。

全局安装会复制 Skill、脚本和格式说明，因此不依赖克隆仓库一直留在原地。规则由 Hook 自动注入，不额外注册到 Skill 选择器，避免模型重复加载并播报技能名称。更新代码后重新运行安装器；已有配置和 Skill 副本各备份一次，其他 Hook 保留。定义改变后重新检查信任状态。自定义 `CODEX_HOME` 会同时用于用户 Hook 配置和默认运行目录。

只想启用单个项目时，仍支持：

```sh
python3 adapt-project-explanations/scripts/install.py --project /work/proj-a
```

单项目模式引用本仓库脚本，移动后需重新安装。新版本全局和本地 Hook 同时启用也只注入一次；已有旧版单项目安装应先重跑安装器更新。用户主目录在没有项目时不会被用作全局记忆文件。

## 实际体验怎么变

| 你在做什么 | Agent 应该怎么回答 | 地图怎么处理 |
|---|---|---|
| 首次问 prefill/decode 区别 | 用通俗的因果解释讲清楚 | 刚讲完不等于掌握，先不记 |
| 能根据 TTFT/TPOT 审阅结果 | 从已有基础继续分析 | 记录这部分窄边界 |
| 不懂“相同文档为何不能复用 KV” | 补“前文改变 → 中间表示改变 → 后层 KV 可能改变” | 不把刚解释的内容立刻写入 |
| 据此把固定文档放在变化问题前面 | 继续讨论实际命中条件 | 记录已应用的知识 |
| 追问最后半个块怎么办 | 深入块粒度 | 保留上层，等后续理解再加子节点 |
| 换话题，或仅说“嗯，先这样” | 正常回应 | 不凭这一点新增掌握 |
| 说明“刚才只是照抄，其实没懂” | 补上缺失连接 | 缩小对应记录，保留其他知识 |

无需复述、测验或逐轮确认。判断依据是自然追问、实际应用和后续相关讨论。

## 记忆文件是什么样

每个项目的 `.know/map.md` 初始只有：

```markdown
# 已掌握
```

下面是本次真实 Codex 对话保存的地图节选；这些知识不会随安装导入：

```markdown
# 已掌握

## 大模型推理性能
- Prefill 与 decode 的阶段区别
- TTFT 与 TPOT
  - 延迟体验与指标区分
- 前缀缓存
  - KV 对前文上下文的依赖
  - 固定系统提示与文档在前、变化问题在后的请求排列
  - 完整块命中与不足一块的公共前缀重算
```

每行只标出知识边界，缩进表示更具体的理解。不保存评分、状态、完整定义、对话原文或学习流水账。没记录不等于不懂，Agent 仍要结合当前问题判断深度。你可以直接查看、纠正文件（UTF-8、LF 换行）。

## 自动运行靠什么

```text
普通项目消息
    ↓ UserPromptSubmit：识别项目、注入 Skill + 地图 + 本轮候选位置
模型回答，并判断这轮是否提供了新的理解证据
    ↓ 有变化才写候选；没有变化就正常结束
Stop：校验格式、检查其他会话是否改过地图
    ↓
原子保存并清理；冲突时请求一次重新合并
```

Skill 决定“怎么解释、什么可以记”；代码保证“每轮加载、合格后保存”。格式正确不能证明用户已经理解，误判靠后续证据或用户修改来纠正。

## 已验证到哪一步

- **真实 Codex**：自动注入、模型写候选、Stop 保存；从空图起步、自然应用后增加层级、新会话使用地图、纠正误判、无更新时无维护播报。
- **真实异常验证**：模型写错格式后被拦截并修复；注入并发改动后重新合并；候选生成后强制中断进程，再恢复清理旧候选。
- **36 项自动回归通过**：中文/空格路径、重复安装、同组 Hook 共存、重复事件、嵌套项目隔离、双进程保存，以及全局/本地同时执行只注入一次、冲突重试不丢基线。
- **独立角色试用**：三个 Agent 扮演指标初学者、向下追问者、跨会话用户，累计 21 次真实 CLI 交互。用户角色是合成的，不等于真实用户审批。[指标](review/persona-metrics.md) · [深度](review/persona-depth.md) · [跨会话](review/persona-transfer.md)

[真实环境与异常证据](review/codex-live-validation.md) · [全局安装与项目隔离验证](review/global-install-validation.md)。原有[行为案例](review/vllm-kv-oneshots.md)仍待用户审批。

本地检查（Windows 将 `python3` 换为 `py -3.9 -X utf8`）：

```sh
python3 -m unittest discover -s adapt-project-explanations/tests -v
python3 adapt-project-explanations/scripts/know.py validate adapt-project-explanations/references/map.example.md
```

可选的真实会话复跑使用当前 Codex 配置与模型额度，在临时 Git 项目中输出证据。先审阅 Hook 代码；此测试驱动对单次调用绕过 Hook 信任，日常使用仍走 `/hooks`：

```sh
python3 adapt-project-explanations/tests/live_codex.py --scenario adapt-project-explanations/tests/scenarios/kv-cache.json
```

驱动退出成功不等于语义测试通过，仍需检查回答、地图与 `hook-events.jsonl`。

## 当前限制与隐私

- 每个项目默认面向同一用户；尚无多人身份隔离。
- 正确表述可能只是照抄。模型也可能漏记、记得过宽或讲得偏长；已验证纠正路径，未证明长期准确率。
- 正常回合不播报维护。异常修复可能产生一次续答或重复回答，不能承诺完全无感。
- 中断候选在同一会话下次输入时清理。永不恢复的会话可能留下临时目录，确认会话结束后可删除；不会自动提交这些候选。
- 锁只协调遵守协议的写入，无法保证外部编辑器恰好在保存瞬间写文件时也没有竞争。
- 生产 Hook 不记录对话原文；地图作为上下文发送到当前配置的模型服务。Codex 自身的会话记录由 Codex 管理。测试驱动会额外保存合成对话证据。

若未自动运行，先检查新会话的 `/hooks` 是否 Active、Python 版本和脚本位置；无写入权限的会话不能保存候选。运行文件加入项目的本地 Git 忽略规则。[完整协议](adapt-project-explanations/references/map-format.md) · [官方 Hook 文档](https://learn.chatgpt.com/docs/hooks)
