# Recovery is a measured property

`checks.x86_64-linux.recovery` exercises `sandhi.retainedRecipes` inside a
disposable NixOS guest. It uses a small fixed-output fixture and Nix's builtin
fetcher, so it does not need a compiler toolchain or an external source server.
Its result is written to `recovery.json` only after every assertion passes.

The experiment checks these distinct propositions:

1. The system closure contains the available fixture's recipe and input, without
   a direct reference to its output. That output is prebuilt for image packaging;
   the guest explicitly realizes its own baseline through the isolated daemon.
   The missing-input recipe is instantiated after boot and given its own explicit
   test GC root; its output is absent.
2. Collection removes an unrooted control while preserving those recipes and
   the declared input. This demonstrates that collection actually ran.
3. The Nix daemon has its own network namespace, containing only loopback and
   no IPv4 route. Every store command explicitly uses that daemon. Substitution
   and remote builders are disabled for realization.
4. The available fixture contains the expected bytes, and ordinary collection
   keeps its output through the retained derivation and keep-outputs policy.
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
The fixture with an unavailable input tests retention in the guest's live store.
[Targeted deletion](https://nix.dev/manual/nix/2.35/command-ref/nix-store/delete.html)
is used for the controlled-loss step; liveness checks remain enabled.

## Image-export limitation, observed

The first CI attempt failed before boot: `exportReferencesGraph`, used by the
NixOS image builder, expands encountered derivations to their outputs, even when
the evaluation context contains only a constant recipe reference. This behavior
is explicit in [Nix's exportReferences implementation](https://github.com/NixOS/nix/blob/2.35.2/src/libstore/store-api.cc).
The original failure is retained as archive record
`fc5b114e02f5ad0e4bc6ea5945e203620cda17a3055490f0606d70685a467dcb`.

The test therefore prebuilds the available fixture through `system.checks`, which
adds a build dependency without an output root. It creates the unavailable recipe
after boot, using the same fixture expression and an explicit guest GC root.
These two retention mechanisms are recorded separately. This test does **not**
claim that an image containing an unbuildable retained recipe can be packaged by
the stock exporter. Live-store retention and image transport have different
requirements.

The next run reached guest boot but disproved a second assumption: a host-side
`system.checks` build does not guarantee that its output is present in the guest.
The test now realizes the baseline through the isolated daemon before collection
and deliberate loss. This initial realization and subsequent restoration have
the same network restrictions. Neither is an independent second-builder claim.

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
