# BOOK · Project Cognition Map

**让 Codex 记住你理解到哪里，下次从那里接着讲。**

BOOK 为 Codex CLI 保存项目知识边界。读代码、分析实验或审阅改动时，Codex 可以从你已经理解的地方接着讲。

| 核心概念 | 职责 |
| --- | --- |
| **Knowledge Boundary · 知识边界** | 用项目里的 `.know/map.md` 记录 Codex 下次可以默认你理解到哪里。 |
| **Evidence-based Update · 按证据更新** | 用户在对话中用自己的推理、应用或纠正提供证据时，更新相应边界。 |
| **Explanation Adaptation · 调整解释** | 从最接近问题的已知知识出发，跳过已掌握部分，先补卡住的因果连接。 |

[快速开始](#快速开始) · [使用示例](#使用示例) · [工作方式](#工作方式) · [常见问题](#常见问题) · [详细文档](#详细文档)

> **状态：可试用。** 已有真实 Codex 会话验证，但理解判断仍由模型推断，可能误记或漏记。它适合在项目讨论中调整解释深度，目前每个项目默认面向同一位用户。

## 快速开始

需要 **Git、Python 3.9+** 和支持 `UserPromptSubmit` / `Stop` Hook 的 **Codex CLI**。脚本只使用 Python 标准库，无需安装额外依赖。

### 1. 获取并安装

Linux / macOS：

```sh
git clone https://github.com/Ben-cpy/BOOK.git
cd BOOK
python3 adapt-project-explanations/scripts/install.py --global
```

<details>
<summary>Windows（PowerShell）</summary>

```powershell
git clone https://github.com/Ben-cpy/BOOK.git
cd BOOK
py -3.9 -X utf8 adapt-project-explanations/scripts/install.py --global
```

可用 `py -0p` 查看 Python 版本，并换用更高版本。

</details>

使用 uv 时，安装命令也可以写成：

```sh
uv run --no-project python adapt-project-explanations/scripts/install.py --global
```

### 2. 在目标项目中启动 Codex

```sh
codex -C /absolute/path/to/your-project
```

将路径换成自己的项目目录；Windows 可使用 `codex -C "C:\path\to\your-project"`。

在启动提示或 `/hooks` 中审阅并信任 **Project Cognition Map** 的 `UserPromptSubmit`、`Stop` 两个 Hook，确认均为 **Active**。如果出现项目信任提示，也需完成授权。

### 3. 照常讨论项目

例如：“我会看 TTFT 和 TPOT，但没想明白前缀缓存为什么要求前文一致，结合这个项目解释一下。”

无需手动调用 Skill。第一次发消息时，Hook 会在该项目创建 `.know/map.md`，初始内容只有 `# 已掌握`。后续有理解证据时才更新，安装不会导入示例知识。

**确认安装成功：** `/hooks` 中两个 Hook 均为 Active，发送一条项目消息后可以找到 `.know/map.md`。地图暂时为空是正常情况。

## 使用示例

假设地图已经记录你理解 prefill / decode，正在研究前缀缓存。以下是预期行为示例，实际措辞取决于模型。

> **你：** 同一篇文档没变，为什么换了开头的问题，后面的 KV 就不能复用？
>
> **Codex：** 文档里的 token 会受到前文影响。开头的问题变了，中间表示也可能改变，进而影响后续层的 KV。因此，文档文字相同不足以保证 KV 相同。

只听完解释，或回一句“明白了”，地图都保持原样。后来你应用了这个关系：

> **你：** 那我把固定系统提示和文档放前面，变化的问题放最后，让文档看到相同的前文。

这提供了更新地图的依据。地图可以逐步形成：

```markdown
# 已掌握

## 大模型推理
- Prefill 与 decode 的分工
- 前缀缓存
  - KV 对前文上下文的依赖
  - 固定内容在前、变化问题在后的请求排列
```

下次问“最后只有半个块怎么办”，Agent 从块粒度继续讲。若你说“刚才只是照抄，其实没懂”，它应缩小相应记录并补上解释。

**每行只标记知识边界，缩进表示更具体的理解。** 无需测验或逐轮确认；地图不写评分、完整定义和对话流水账。未记录的知识仍由当前对话判断。

## 工作方式

```text
发消息 → UserPromptSubmit 加载当前项目地图与 Skill
       → Agent 回答；有新理解证据时写候选地图
       → Stop 检查格式与并发改动，通过后保存
```

Hook 负责项目隔离、文件锁、格式校验和原子保存。模型负责判断对话证据，以及哪条知识会改变下一次解释。

全局安装复制规则和脚本到 `~/.codex/cognition-runtime/adapt-project-explanations/`，并在 `~/.codex/hooks.json` 注册触发器。设置了 `CODEX_HOME` 时使用该目录。地图始终保存在各项目内：

```text
project-a/.know/map.md   # A 项目的知识边界
project-b/.know/map.md   # B 项目的知识边界
```

规则由 Hook 自动注入，因此不会重复注册到 Skill 选择器。Git 子目录沿用仓库根目录的地图；非 Git 项目第一次请从项目根目录启动。[安装、边界与故障排查 →](docs/usage.md)

## 常见问题

**如何更新？** 在克隆的 BOOK 仓库内执行 `git pull --ff-only`，再运行原来的安装命令。安装器保留其他 Hook 和已有地图，首次覆盖前备份配置与旧运行副本；Hook 定义变化后需重新检查信任。

**能只启用一个项目吗？** 可以：`python3 adapt-project-explanations/scripts/install.py --project /absolute/path/to/project`。此模式引用克隆仓库里的脚本，移动仓库后需要重新安装。

**为什么地图没有更新？** 地图只在对话出现能改变知识边界的证据时更新。遇到运行问题，可检查 `/hooks` 是否 Active、会话是否有写入权限，再查看[排查步骤](docs/usage.md#故障排查)。

**会保存或发送什么？** 生产 Hook 保存知识边界与更新用的临时文件，不记录完整对话。地图会作为上下文发送给当前配置的模型服务；Codex 自身的会话记录由 Codex 管理。[隐私与限制](docs/usage.md#限制与隐私)

## 详细文档

| 文档 | 内容 |
| --- | --- |
| [使用指南](docs/usage.md) | 安装位置、项目边界、更新、停用、排查与限制 |
| [Skill 规则](adapt-project-explanations/SKILL.md) | 解释深度、理解证据与纠正方式 |
| [地图与 Hook 协议](adapt-project-explanations/references/map-format.md) | 格式约束、并发检查与事件契约 |
| [真实 Codex 验证](review/codex-live-validation.md) | Windows 真实会话、异常恢复与剩余问题 |
| [全局安装验证](review/global-install-validation.md) | 跨项目隔离与重复安装 |
| [本次本地验证](review/linux-install-validation.md) | Linux 回归检查、安装与 Hook 冒烟验证 |
| [README 参考记录](review/readme-references.md) | 5 个超过 10k stars 的 Skill 项目与本次写作取舍 |

已有 Windows 验证使用 Codex CLI 0.164.0、Python 3.9.13、gpt-6-astra，包含 36 项回归检查与 21 次模拟用户 CLI 交互。模拟用户试用不等于真实用户验收；本次 Linux 检查范围见本地验证记录。
