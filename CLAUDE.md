# Working notes for Claude

## Keep `TESTER_COMMENTS.md` up to date

Whenever a change is made because the user reported something — a bug, a complaint, a
"this looks wrong", a request for a feature they found missing — add it to
`TESTER_COMMENTS.md` as part of the same piece of work, not as a separate task to be asked
for. The file feeds a reviewer-comments write-up, so it is kept in the tester's voice:

- **Newest round at the top.** New rounds get a `## Round N — short description` heading
  and a `*Shipped in: —*` line, filled in once the version is known.
- **Quote the complaint first**, as a blockquote, in the words the user actually used,
  tidied for grammar but not translated into engineering language.
- **Then `**What changed.**`** in plain terms — what the person will notice is different.
  No file names, no function names, no library names, no numbers the reader can't check.
- Where something was deliberately *not* changed, say so and why.
- Where the fix revealed a process failure worth owning (a test asserting the bug, a
  problem that escaped to the user), record it under the entry. The write-up is more
  credible with those in it than without.
- Keep the **Still open** section at the bottom honest and current.

Do not fabricate a version number for the `Shipped in:` line. If the release it went out
in isn't known, leave the em-dash and say so in the reply.

## Things not to commit

`.gitignore` covers these; do not work around it.

- The signing keystore (`*.jks`, `*.keystore`, `key.properties`).
- The ONNX models under `sketch_assistant/assets/models/` — `scripts/download_models.py`
  fetches them and the workflows run it before building.

## Testing habits that this project earned the hard way

- **Synthetic fixtures flatter the code.** The first hands implementation passed every
  synthetic test and then lost whole fingers on the first real photograph. Test against
  the photos in `tests/fixtures/`.
- **Verify every regression test by reintroducing the bug.** A test written after a fix
  that has never been seen to fail is not evidence. Several tests in this repo were
  discarded for proving nothing once that check was applied; one was asserting the bug.
- **Measure rather than eyeball**, and run a control where the claim is comparative.
