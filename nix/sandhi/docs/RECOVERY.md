# Recovery is a measured property

`checks.x86_64-linux.recovery` exercises `sandhi.retainedRecipes` inside a
disposable NixOS guest. It uses a small fixed-output fixture and Nix's builtin
fetcher, so it does not need a compiler toolchain or an external source server.
Its result is written to `recovery.json` only after every assertion passes.

The experiment checks these distinct propositions:

1. The system closure contains two recipes and the available fixture's input.
   Neither output is present at the start.
2. Collection removes an unrooted control while preserving those recipes and
   the declared input. This demonstrates that collection actually ran.
3. The Nix daemon has its own network namespace, containing only loopback and
   no IPv4 route. Every store command explicitly uses that daemon. Substitution
   and remote builders are disabled for realization.
4. The available fixture builds, and ordinary collection keeps its output.
5. One test-only deletion, with `keep-outputs=false` scoped to that command,
   removes this synthetic output. Its recipe and source remain. Realization
   restores the expected payload and the same NAR hash.
6. The other recipe remains present but cannot build because its file input is
   unavailable. Its recovery status stays unresolved; retention earns no success
   claim on its own.

The deletion operates only on the named synthetic output in the writable guest
store. It is an explicit simulated-loss operation, not a change to Sandhi's
default policy. No live host data, source archive, or production state is removed.

## Why recipe references need care

Nix gives `.drvPath` a deep string context that includes output dependencies.
`kosa.nix` uses `builtins.unsafeDiscardOutputDependency` to retain a constant
reference to the recipe instead. The recipe's input references remain tracked;
its outputs need not build merely to retain it. Global `keep-outputs` separately
protects realized outputs while their derivations remain live.

This distinction is described in the [Nix builtin documentation](https://nix.dev/manual/nix/2.35/language/builtins.html#builtins-unsafeDiscardOutputDependency).
The fixture with an unavailable input checks that packaging the guest does not
accidentally require that output. [Targeted deletion](https://nix.dev/manual/nix/2.35/command-ref/nix-store/delete.html)
is used for the controlled-loss step; liveness checks remain enabled.

## Limits

A pass demonstrates restoration of this fixture under the recorded conditions.
It does not demonstrate off-host backups, restoration after storage corruption,
availability of every compiler/source dependency, database rollback, or recovery
of arbitrary packages. A constant recipe reference preserves the reference
closure; it does not create any missing bytes. The test's second recipe is the
counterexample carried beside the successful one.

See `VALIDATION.json` and the original CI artifacts for observed results and
the exact tested revision. Evaluation and a built test driver alone are not a
successful recovery test. This experiment never establishes builder independence
or changes canonical status.
