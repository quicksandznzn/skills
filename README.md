# skills

A personal collection of Agent Skills. See [`upstreams.md`](./docs/upstreams.md).

## Install

Install all skills:

```bash
npx skills add quicksandznzn/skills
```

Install one skill:

```bash
npx skills add quicksandznzn/skills --skill design-taste-frontend
```

List available skills:

```bash
npx skills add quicksandznzn/skills --list
```

## Upstream updates

The sync workflow runs daily at 06:00 Asia/Taipei and can also be run manually.
It collects all pending upstream updates into one pull request on
`feat/sync-upstreams`, rebuilding the branch from the latest `main` on each run.
The pull request stays open for manual review and merging. If no updates remain,
the workflow closes the existing sync pull request.
