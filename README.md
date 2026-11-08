# Project Cognition Map

**让 Codex 从你已经理解的地方接着讲。**

一个为 Codex CLI 提供项目级理解记忆的 Skill。读代码、分析实验、审阅改动时，它从自然对话中判断你已经掌握哪些知识，让 Agent 省掉熟悉的基础，把缺失的因果关系讲清楚。

全局安装一次，每个项目维护自己的 Markdown 地图。换会话可以继续使用；不同项目的理解边界分开保存。

[使用示例](#使用示例) · [快速开始](#快速开始) · [工作方式](#工作方式) · [文档](#文档)

## 使用示例

假设你已经能区分 prefill 和 decode，正在研究前缀缓存。下面是一段示意对话。

**你问：**

> 同一篇文档一个字没变，为什么换了开头的问题，后面的 KV 就不能复用？

**Codex 从你卡住的地方解释：**

> 文档里的 token 会受到前文影响。开头的问题变了，模型算出的中间表示也可能改变，进而影响后续层的 KV。所以即使文字相同，也不能仅凭文档相同就复用旧 KV。

此时不会因为“已经解释过”就把这项记为掌握。后来你继续应用：

> 那我把固定的系统提示和文档放前面，把每次变化的问题放最后，让文档看到相同的前文。

这才提供了更新地图的依据。项目的 `.know/map.md` 可以逐步形成这样的树：

```markdown
# 已掌握

## KV cache
- Prefill 与 decode 的分工
- 前缀复用
  - 相同文本在不同前文下的 KV 可能不同
```

下次追问“最后只有半个块怎么办”，Agent 从块粒度继续讲，保留已有的上层知识；等后续讨论表明你也理解了这一层，再增加子节点。

**每行只记录知识边界，缩进表示理解深度。** 不需要测验、复述或逐轮确认。地图不写评分、完整定义和对话流水账；你可以随时查看和纠正。

## 快速开始

需要 **Git、Python 3.9+**，以及支持 `UserPromptSubmit` 和 `Stop` Hook 的 **Codex CLI**。

### 1. 获取仓库

```sh
git clone https://github.com/Ben-cpy/BOOK.git
cd BOOK
```

### 2. 全局安装

**Windows**

```powershell
py -3.9 -X utf8 adapt-project-explanations/scripts/install.py --global
codex -C "C:\path\to\your-project"
```

可用 `py -0p` 查看已安装的 Python，并换用更高版本。

<details>
<summary>Linux / macOS（本轮未实测）</summary>

```sh
python3 adapt-project-explanations/scripts/install.py --global
codex -C /work/proj-a
```

</details>

### 3. 启用并开始对话

在 Codex 的启动提示或 `/hooks` 中，审阅并信任 **Project Cognition Map** 的 `UserPromptSubmit`、`Stop` 两个 Hook，确认均为 **Active**。如果提示项目信任，也需完成授权。

随后照常讨论项目，无需手动调用 Skill。首次使用时，该项目的 `.know/map.md` 从只有 `# 已掌握` 的空地图开始，随对话逐步更新；上面的示例知识不会自动导入。

安装器保留已有地图和其他 Hook。升级时拉取仓库更新，再运行一次安装命令；若 Hook 定义改变，需要重新审阅信任。

## 工作方式

1. **读当前项目的地图。** 你发消息时，Hook 自动注入 Skill 规则和已掌握的知识边界。
2. **从合适的深度回答。** Agent 结合地图与当前问题决定省讲什么、补讲什么。没有记录的知识，仍由当前对话判断。
3. **有新证据才更新。** 正确应用、后续相关讨论可以支持新增节点。仅仅换话题不会自动新增；发现误判就缩小记录。候选地图通过格式与并发检查后才保存。

全局安装的是规则和触发器，记忆文件始终属于项目：

```text
/work/proj-a/.know/map.md   # A 项目的理解边界
/work/proj-b/.know/map.md   # B 项目的理解边界
```

Git 项目的子目录沿用仓库根目录的地图。非 Git 项目第一次请从项目根目录启动。只想启用单个项目，也可以用 `--project <项目路径>` 替代 `--global`。

## 验证与当前边界

已在 **Windows · Codex CLI 0.164.0 · Python 3.9.13 · gpt-6-astra** 下验证自动注入、模型更新、Stop 保存和跨项目隔离，**36 项回归检查通过**。三个模拟用户角色还进行了 21 次真实 CLI 交互。[查看测试与实际地图变化 →](review/codex-live-validation.md)

理解判断仍由模型推断，可能记得过宽或解释偏长；异常修复时也可能产生一次续答。模拟用户试用不等于实际用户验收，其他平台与模型尚未实测。

地图会作为上下文发送给你配置的模型服务；生产 Hook 不保存完整对话。每个项目目前默认由同一位用户使用。

## 文档

- [Skill 规则](adapt-project-explanations/SKILL.md) — 如何选择解释深度、判断理解和修正记录。
- [安装细节与地图格式](adapt-project-explanations/references/map-format.md) — 项目边界、单项目安装、临时文件与 Hook 协议。
- [真实 Codex 验证](review/codex-live-validation.md) — 完整对话、发现的问题、修复与剩余限制。
- [全局安装与项目隔离](review/global-install-validation.md) — 不同项目各自保存和读取地图的实测证据。
