# Rounds

A round is one unit of work on this repository: one brief in, one report out, the owner commits.

1. **Brief.** The owner writes `rounds/<YYYY-MM-DD>-brief-<topic>.md`: context, decisions already made, work items with exact paths, verification, out of scope, stop conditions, report shape.
2. **Work.** An agent (or a contributor) does the work in the working tree, following `AGENTS.md`. It does not commit or push.
3. **Report.** The agent writes `rounds/<YYYY-MM-DD>-report-<topic>.md` in the shape the brief asks for, ending with the exact `git add` list and a suggested commit message.
4. **Review and commit.** The owner reads the report, not the whole diff, checks the verification output, and commits.

One work package per round; two only when they are small and share files. Briefs and reports are kept; they are the project's working history.
