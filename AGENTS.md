# Repository rules

- Put original skills in `skills/<frontmatter-name>/`; the folder and frontmatter `name` must match.
- Treat destinations declared in `upstreams.json` as read-only mirrors. Create a separately named skill for local adaptations.
- Add third-party sources through `upstreams.json`, record their license name there, then run `python3 scripts/sync_upstreams.py`.
- Before finishing, run `python3 scripts/sync_upstreams.py --check` and `npx --yes skills@1.5.23 add . --list`.
