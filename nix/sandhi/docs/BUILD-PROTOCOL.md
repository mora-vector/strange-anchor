# Named objects, separate evidence

The implemented checks are `checks.x86_64-linux.evaluation` and
`checks.x86_64-linux.reachability`. The latter builds and boots a test VM, executes
probes inside generated services, and writes `reachability.json` into its output.
Neither check is a production vessel deployment.

## One realization

With Nix installed and flakes enabled:

```sh
nix flake check --no-build .
nix build --out-link result-evaluation .#checks.x86_64-linux.evaluation
nix build --out-link result-reachability .#checks.x86_64-linux.reachability
cat result-reachability/reachability.json
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
record successful restoration separately. No archive restoration has been run.

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
A failed VM launch remains a failed step; the recorder never promotes it to a
successful runtime test or an independent attestation.

## Repository CI

The `Validate Sandhi` workflow executes this recorder on Ubuntu for relevant
pull requests and main-branch changes. It pins checkout, the Nix installer
action, and the evidence uploader to commit SHAs, and installs Nix 2.35.2. The
installer enables KVM when available; this is a facility request, not proof that
a guest ran. A job passes only if the recorder completes both builds and finds
the guest observation file. Logs are printed during builds and retained even
when a step fails. Artifacts expire after 30 days; copy evidence to a durable
archive before expiry.

Source digests include Nix files, the lock, and the recorder. When available,
the report records the Git commit and any source changes. GitHub may test a
synthetic PR merge commit; use the recorded commit and file digests when
identifying the exact input. CI neither signs builder claims nor promotes
canonical status.
