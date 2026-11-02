---
name: escalation-draft
description: Turn a question only people can answer into an escalation register entry, addressed to roles, with the facts it is about. Use when evidence cannot settle a fact and the owner or another role must decide.
---

# escalation-draft

## When to use

Two sources of the same rank disagree, a document is silent, or a fact needs a decision the agent may not take (any widening of access is always the owner's).

## Steps

1. Check it is not already asked: `grep -l "<entity>.<key>" registers/escalations/*.yaml`.
2. Write `registers/escalations/E-NNNN.yaml` with the next free number (numbers are never reused):
   - `question`: one question, answerable in a sentence;
   - `asked_to`: roles, never names (for example `data-owner`, `platform-engineer`);
   - `status: open`, `asked_on`, `about` (the entity or relationship refs);
   - `records`: the evidence that shows the conflict or the gap, quoted.
3. Mark the facts it is about `unresolved` if no usable evidence remains, so projection labels them `unresolved` and no layer joins them.
4. `fact check --root <dir>`.
5. When an answer comes back, it goes in `answer` (`text`, `source` registered in `sources/`, `answered_on`, `evidence`) and `status: answered`; the `registers` stage refuses an answer without usable evidence.

## Report

The escalation id, the question, who it is addressed to, and which facts wait on it.
