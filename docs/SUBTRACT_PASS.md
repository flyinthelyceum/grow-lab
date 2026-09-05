# Subtract pass: the brief

Status: NOT YET RUN. Jared asked for this on 2026-09-04. Run it before the next
hardware order.

## Why this exists

On the CNC station the build went from a 17-solid carcass to 118 solids in a single
session: parts 55 to 63, BOM $2,401 to $2,635, and the tell nobody was watching,
standing notes 45 to 59 — constraints that must stay true and that nothing enforces.
Not one thing was removed all day.

Jared's diagnosis, now a standing rule across projects:

> generative ai is far better at adding than refining. We need to incorporate some
> simplification, refining, and clean up passes to our workflows.

He says grow-lab is in the same place, with the BOM expanded well beyond scope.

Every agent in a build loop is rewarded for producing something. None is rewarded for
deleting something. Left alone the loop only accretes, and the accretion is invisible
because each addition was individually justified.

## The constitution, binding on every agent in the pass

- You may only DELETE, MERGE, or REPLACE-WITH-SIMPLER. Proposing a new part, file,
  sensor, script, check or standing note is out of scope by construction. If a cut
  needs a small addition to work, that is a MERGE and must show a net reduction.
- NOTHING IS PROTECTED. The sensor set, the dashboard, the enclosure, the schema, the
  deployment, the docs, prior rulings: all of it may be questioned. Exception in kind,
  not in scope — anything affecting plant survival or electrical safety may be
  proposed, but must be labelled explicitly and left to Jared.
- "Nothing to cut here" is a valid and respected finding. Padding the list with
  cosmetics is a failure.
- Every cut names: what is deleted, the count it moves, what capability is honestly
  lost, and what breaks. If the only thing that breaks is a standing note, say so.
  That is the strongest kind of cut.
- The pass produces a PROPOSAL Jared marks up. It does not execute changes.

## The method

1. **Baseline.** Count, do not estimate, and say how you counted: BOM lines and total
   cost, parts, sensors, scripts and services, LOC, config entries, schema tables and
   columns, dashboard views, docs pages, and how many separate things a person must
   understand to run it.
2. **Lenses, in parallel, each blind to the others,** over disjoint territory:
   first principles (what is grow-lab actually for, what is the smallest thing that
   does that, diff it against what exists — this lens alone may question whole
   subsystems), hardware and BOM, sensing and data, software and services, enclosure
   and fabrication, and the record (docs, config, standing constraints, dead params).
3. **A defender for every single proposed cut.** Its job is the strongest honest case
   for KEEPING the thing, after which it judges fairly whether the cut survives, and
   corrects the proposer's claimed counts against the actual files. A cut survives only
   if complexity removed still exceeds capability lost. Kill cuts that rest on a
   misreading, or whose "capability lost: none" is false. On the CNC pass the lenses
   proposed 77 cuts and every one got its own defender. That ratio is the point.
4. **Rank into tiers:** FREE (no capability lost, do it), CHEAP (trivial loss,
   recommended), REAL-TRADE (a genuine capability goes, Jared decides), JAREDS-CALL
   (touches a ruling he made, or is survival/safety affecting). Order within a tier by
   counts moved. Merge duplicate findings across lenses.

## The deliverable

A Google Doc in the grow-lab Drive folder, linked to Jared. Not a filesystem path: he
reads from a phone and a laptop and cannot open a path on the Pi or the mini without
shelling in.

It contains: the before/after table against the baseline; the tiered cut list; a short
section on cuts that did NOT survive their defence, so nobody re-proposes them; and a
blunt section naming where grow-lab is irreducibly complicated and why, so the pass is
not read as "everything can go".

Read-only on the repo. Analysis and proposal only, no commits.
