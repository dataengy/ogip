# `.ai/` — agentic hub

Discovery hub for AI agents and humans working on OGIP. Root `AGENTS.md` symlinks here.

| File / dir | Purpose |
|---|---|
| [AGENTS.md](AGENTS.md) | **Start here.** General rules, hard rules, conventions, run profiles. |
| [CLAUDE.md](CLAUDE.md) | Claude Code workflow notes (commands, gates). Root `.claude/CLAUDE.md` symlinks here. |
| [PLAN.md](PLAN.md) | Master creation plan — target design + phased build + locked decisions. |
| [TODO.md](TODO.md) | Short ordered checkboxes of near-term actions; references tasks/phases. |
| [FIXME.md](FIXME.md) | **Known conflicts and debt, high priority** — document contradictions, convention gaps, things not to silently step over. |
| [STATUS.md](STATUS.md) | Live status: current phase, last done, next steps, decision log. |
| [tasks/](tasks/) | Per-phase and one-off task files (working notes, checklists). |

Convention: durable rules → `AGENTS.md`; live state → `STATUS.md`; near-term actions →
`TODO.md`; known contradictions and debt → `FIXME.md`; the roadmap → `PLAN.md` and
[../docs/ROADMAP.md](../docs/ROADMAP.md). Tasks sync to GitHub Issues/Projects via
`just tasks-sync`.
