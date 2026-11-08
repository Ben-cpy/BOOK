# Project Cognition Map
Project: vllm-kv

## 前缀复用
- [可直接讲] 前缀一致性与连续命中 <!-- prefix-match | used | s01:t02 -->
  - [待厘清] 未填满的块能否跨请求复用 <!-- partial-block | frontier | s01:t04 -->
- [补桥] 命中对首 token 与后续生成延迟的影响 <!-- latency-scope | repeated | s01:t06, s01:t08 -->
