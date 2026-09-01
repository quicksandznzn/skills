# skills

个人维护的 Agent Skills 集合，可通过 [`skills`](https://github.com/vercel-labs/skills) CLI 安装。

A personal collection of Agent Skills, installable with the [`skills`](https://github.com/vercel-labs/skills) CLI.

## 安装 / Install

安装全部 skills / Install all skills:

```bash
npx skills add quicksandznzn/skills
```

安装单个 skill / Install one skill:

```bash
npx skills add quicksandznzn/skills --skill design-taste-frontend
```

只查看可用 skills / List available skills:

```bash
npx skills add quicksandznzn/skills --list
```

## Skills

<!-- upstreams:start -->
| Skill | 来源 / Source | 固定提交 / Pinned commit | License |
| --- | --- | --- | --- |
| `design-taste-frontend` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill/tree/main/skills/taste-skill) | [`ccbc15639c97`](https://github.com/Leonxlnx/taste-skill/commit/ccbc15639c97057cbfcf32ecebc38ef716e4bb37) | MIT |
<!-- upstreams:end -->

第三方 skill 保持上游原样；来源、固定 commit 和许可证名称记录在本页及 `upstreams.json`。自动同步只会创建待审核的 pull request，不会自动合并。

Third-party skills remain unchanged from upstream; provenance, pinned commits, and license names are recorded here and in `upstreams.json`. Automated syncs only open pull requests for review; they never merge automatically.

## 维护 / Maintenance

检查当前镜像 / Verify current mirrors:

```bash
python3 scripts/sync_upstreams.py --check
```

拉取上游更新 / Pull upstream updates:

```bash
python3 scripts/sync_upstreams.py
```

本仓库脚本和原创 skills 使用根目录的 MIT 许可证。第三方 skill 继续适用其上游许可证。

Repository scripts and original skills use the root MIT license. Third-party skills remain subject to their upstream licenses.
