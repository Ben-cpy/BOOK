# Local map format

A map contains a project ID, topic headings, and nested boundary labels. See the [synthetic example](map.example.md). The visible tree answers where the next explanation can start. Inline comments store only a stable node ID, an update reason, and the supporting user-turn IDs.

To enable a project on request, create .know/map.md with just the title and Project line. Keep this directory outside tracked project content, for example through a local Git exclude. Sample identifiers are synthetic.

The exact row syntax is:

```markdown
- [可直接讲] 前缀一致性与连续命中 <!-- prefix-match | used | s01:t02 -->
  - [待厘清] 未填满的块能否跨请求复用 <!-- partial-block | frontier | s01:t04 -->
```

Use printable UTF-8, LF newlines with a final newline, one blank line before each topic heading, and two spaces for each deeper level. Topic names and boundary labels are short, with a limit of 56 characters. The map allows 24 boundaries and at most four boundary levels. Node IDs must be unique among siblings. Project IDs, node IDs and the two parts of a session:turn ID are lowercase ASCII slugs of up to 48 characters.

| State | Reason | Distinct user turns |
| --- | --- | --- |
| 可直接讲 | used | 1 |
| 可直接讲 | continued | 2 |
| 待厘清 | frontier | 1 |
| 补桥 | repeated | 2 |
| 补桥 | reopened | 1 |

A new frontier requires a direct parent. A frontier can move to direct or to bridge. A bridge can move to direct. A direct boundary can reopen as a bridge. A frontier promoted to bridge may reuse the frontier's source as the first of its two turns. Automatic updates preserve labels and ordering and touch one boundary.

## Commands

Set cognition_skill_dir to the directory containing SKILL.md.

```sh
python3 "$cognition_skill_dir/scripts/know.py" validate .know/map.md --project vllm-kv
python3 "$cognition_skill_dir/scripts/know.py" apply .know/map.md --project vllm-kv \
  --candidate "$cognition_candidate" --expected-sha256 "$cognition_snapshot_sha" \
  --user-turns "$cognition_host_index"
```

For a write, copy the live map to a temporary snapshot, validate that copy to get its SHA-256, and produce the candidate from that snapshot. The host index is an ordered JSON object like {"project":"vllm-kv","user_turns":["s01:t02","s01:t04"]}. It must come from the host and include both the old and proposed evidence for a transition. The script checks membership and chronology against this input. The host establishes which turns really came from the user.

The local validator uses only the Python standard library. Applying a change uses a POSIX lock for concurrent script writers and atomic replacement. This repository provides an explicit skill invocation and an apply interface. A host hook and trusted index producer are integration work. Keep live maps, lock files, and real host indices out of version control.
