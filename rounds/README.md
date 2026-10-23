# Rounds

A round is one unit of work on this repository: one brief in, one report out, one commit.

1. **Brief.** The owner writes `rounds/<YYYY-MM-DD>-brief-<topic>.md`: context, decisions already made, work items with exact paths, verification, out of scope, stop conditions, report shape.
2. **Work.** An agent (or a contributor) does the work in the working tree, following `AGENTS.md`. It never pushes.
3. **Report.** The agent writes `rounds/<YYYY-MM-DD>-report-<topic>.md` in the shape the brief asks for.
4. **Commit.** The agent makes one commit with the work and the report (D-008). It never pushes, amends or rewrites history.
5. **Review and push.** The owner reads the report and the log, not the whole diff, checks the verification output, and pushes.

One work package per round; two only when they are small and share files. Briefs and reports are kept; they are the project's working history.
