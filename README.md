# BOOK- · Project Cognition Map

**同一个项目做得越深，AI 越应该知道该从哪一层讲起。** 这套 Skill 把解释的起点记成一棵小树。你照常问项目、审阅结果，AI 只在某个卡点影响当前判断时补一小段。

## 五分钟审阅

假设你在看 vLLM 的前缀缓存。下面三行就是你会维护的内容：

- **可直接讲** · 前缀一致性与连续命中
  - **待厘清** · 未填满的块能否跨请求复用
- **补桥** · 命中对首 token 与后续生成延迟的影响

每行只有状态和知识边界。真实格式还用一条折叠在 Markdown 渲染之外的注释保存最小出处。定义、解答和对话原文留在各自的项目材料里。看一眼[示例地图](adapt-project-explanations/references/map.example.md)。

### 两次对话就能看出设计差异

**反复卡在同一层。** 你问「开头换了，后面同样的文档还能接着命中吗？」AI 从你可以跟上的机制讲起：自回归模型里，文档位置会看到前面的 token。开头改变时，后面的字虽然一样，算出的上下文 KV 仍可能不同，所以 vLLM 标准 APC 会把上游前缀计入块身份。地图上只加「开头变化后相同文档能否接续命中」。

**已经懂大流程，开始追更细的区别。** 你问「前缀一致我懂了，最后只填半个块呢？」AI 回答完整块的复用边界，把这个问题放到「前缀一致性与连续命中」下面。下次可以直接从块粒度讲起，父节点仍然可直接用。

听过一次桥以后，你在同类任务里自然往前走两次，Skill 就默认把这段省掉。换题不计入这两次。同一处后来又卡住，可以恢复补桥。看[四个待审批 one-shot](review/vllm-kv-oneshots.md)。

### 哪些行为能硬性检查

| 环节 | 责任 |
| --- | --- |
| **模型** | 看懂是同一层卡住、向下追问，还是已经能继续审阅。选合适的解释起点，并提出一处更新。 |
| **脚本** | 校验 Markdown 树、状态迁移、消息 ID 在项目索引中的顺序，以及文件版本。自动更新每次只动一个节点。 |
| **运行环境** | 提供可信的用户消息索引，日后可通过 Hook 触发检查。当前原型支持显式调用和本地校验。没有索引时，Skill 只在当前对话里调整。 |

硬校验能阻止坏结构和无出处的写入。模型是否选对了边界，需要用案例回放来审。

## 验证

```sh
python3 adapt-project-explanations/scripts/know.py validate \
  adapt-project-explanations/references/map.example.md --project vllm-kv
python3 -m unittest discover -s adapt-project-explanations/tests -v
```

[Skill 规则](adapt-project-explanations/SKILL.md) · [地图格式与写入接口](adapt-project-explanations/references/map-format.md)
