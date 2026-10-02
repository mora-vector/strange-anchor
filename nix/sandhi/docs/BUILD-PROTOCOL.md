# Named objects, separate evidence

The implemented checks under `checks.x86_64-linux` are evaluation, reachability,
recovery, budgets, workload, and applicability. The latter five boot disposable guests and
produce their respective named JSON observation files. Evaluation also runs the
Python unit suite, validates a generated export, and checks legacy compatibility.
The recovery experiment tests limited offline restoration and carries
an unavailable-input counterexample; see [RECOVERY.md](RECOVERY.md).
None of these checks is a production vessel deployment.

## One realization

With Nix installed and flakes enabled:

```sh
nix flake check --no-build .
nix build --out-link result-evaluation .#checks.x86_64-linux.evaluation
nix build --out-link result-reachability .#checks.x86_64-linux.reachability
nix build --out-link result-recovery .#checks.x86_64-linux.recovery
cat result-reachability/reachability.json
cat result-recovery/recovery.json
```

The test permits software emulation where KVM is unavailable. Nix may require
`nixos-test` among the local builder's configured system features. This label is
not evidence of virtualization support; a completed test is the evidence.
Keep the result links as GC roots until their evidence is copied elsewhere.

## Repeatability and independence

Record the exact source bundle/commit, flake.lock, target derivation, Nix version,
platform, dependency-cache policy, output paths, output NAR hashes, and logs.

```sh
nix path-info --json ./result-evaluation
nix build --rebuild .#checks.x86_64-linux.evaluation
```

A local rebuild checks repeatability, not infrastructure independence. A check
output containing VM logs may itself differ byte-for-byte between successful
runs (timings and logs are observations). Compare the named application/system
artifact for reproducibility, and compare structured test assertions for behavior;
do not demand identical timestamps as a correctness criterion.

For a second build, use a separately administered builder. Disable substitution
for the artifact under test and ensure it is either absent from that builder's
store or explicitly rebuilt. A global `--option substitute false` also prevents
substitution of missing dependencies and may require a costly toolchain rebuild;
record that scope deliberately. Shared dependency binaries narrow independence.

Two operators sign their actual reports with their own managed keys. No keys
are attributed to model personas. `lib.saksya` compares reported hashes only;
it neither checks signatures nor promotes releases. Automatic quorum promotion
remains unimplemented. No result in this bundle establishes a second independent
build or safety/correctness from hash agreement alone.

## Retention and recovery

`sandhi.retainedPackages` retains selected outputs through the system closure.
`sandhi.retainedRecipes` retains selected `.drv` paths there and enables global
`keep-outputs`. This can significantly enlarge retention beyond the named set.
A retaining system generation must remain rooted. An unavailable source is not
recreated by rooting its recipe. Back up retained bytes and references off-host;
record successful restoration separately. The synthetic recovery check is not an
off-host archive restoration; no such restoration has been run.

## Evidence archive

Preserve both original contributions, later retractions, and executable revisions.
Reachable Git commits plus independent backups can support that archive. Git
history alone is not a permanence guarantee. The documentary merge type sees only
definitions surviving Nix priority filtering; it cannot reconstruct overridden
claims. Preserve source records outside the merged configuration.

## First-realizer recorder

From the unpacked source directory, run:

```sh
python3 scripts/realize.py --output-dir ../sandhi-run-001
```

Choose a new directory outside the source tree for each run. The recorder saves
source-file digests, commands, exit codes, build output identities, NAR metadata,
and (on success) the packet observations. Its result links retain built outputs.
Use `--evaluation-only` when deliberately collecting only evaluation evidence.
A failed VM launch remains a failed step; the recorder lists completed checks and never promotes failure to a
successful runtime test or an independent attestation.

For a bounded follow-up, select the unresolved experiment explicitly:

```sh
python3 scripts/realize.py --check recovery --output-dir ../sandhi-recovery-002
```

`--check` may be repeated; omitting it runs all six checks. A selected
subset gets `selected-checks-passed`, never the full-suite success label. Reports
record requested and completed checks separately, and print a compact status plus
the failed step's final 40 stderr lines into the job log. The complete logs remain
in the evidence directory. This reduces artifact-download dependence during a
handoff without substituting a summary for original evidence.

The recorder also compares source digests at the start and end. A difference
leaves the individual observations intact but fails the aggregate report, with
both digest maps retained. Run against a fixed checkout: endpoint comparison is
not a filesystem lock and cannot detect a transient edit that was reverted.

## Repository CI

The `Validate Sandhi` workflow executes this recorder on Ubuntu for relevant
pull requests and main-branch changes. It pins checkout, the Nix installer
action, and the evidence uploader to commit SHAs, and installs Nix 2.35.2. The
installer enables KVM when available; this is a facility request, not proof that
a guest ran. A job passes only if the recorder completes all six builds and finds
all five guest observation files. Logs are captured during builds and retained even
when a step fails. Artifacts expire after 30 days; copy evidence to a durable
archive before expiry.

Source digests include Nix files, the lock, and the recorder. When available,
the report records the Git commit and any source changes. GitHub may test a
synthetic PR merge commit; use the recorded commit and file digests when
identifying the exact input. CI neither signs builder claims nor promotes
canonical status. Recorder schema 5 includes standalone schema files in the source
digest map. Older three-check selections cannot claim the expanded suite passed.
See REPORT-COMPARISON.md for the separate opt-in comparison format.
