{ lib }:
let
  prakrtibhava = import ../lib/prakrtibhava.nix { inherit lib; };
  compare = import ../lib/saksya.nix { inherit lib; };
  base = { options.claim = lib.mkOption { type = prakrtibhava lib.types.str; }; };
  merged = (lib.evalModules { modules = [ base
    { _file = "sideband.nix"; claim = "grammar"; }
    { _file = "tessera.nix"; claim = "contracts"; }
  ]; }).config.claim;
  forced = (lib.evalModules { modules = [ base
    { _file = "sideband.nix"; claim = "grammar"; }
    { _file = "override.nix"; claim = lib.mkForce "replacement"; }
  ]; }).config.claim;
  invalidClaim = builtins.tryEval (builtins.deepSeq (lib.evalModules {
    modules = [ base { claim = 42; } ];
  }).config.claim true);
  ordinaryConflict = builtins.tryEval (builtins.deepSeq (lib.evalModules {
    modules = [
      { options.port = lib.mkOption { type = lib.types.port; }; }
      { port = 1000; } { port = 2000; }
    ];
  }).config.port true);
  r = {
    builderId = "a";
    drvPath = "/nix/store/00000000000000000000000000000000-example.drv";
    outputs = [{
      path = "/nix/store/11111111111111111111111111111111-example";
      narHash = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
    }];
  };
  second = r // { builderId = "b"; };
  changed = second // { outputs = map (o: o // {
    narHash = "sha256-BAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";
  }) r.outputs; };
  cases = {
    separateClaims = builtins.length merged == 2;
    retainedOrigins = builtins.sort builtins.lessThan (map (d: d.source) merged)
      == [ "sideband.nix" "tessera.nix" ];
    invalidClaimRejected = !invalidClaim.success;
    ordinaryConflictRejected = !ordinaryConflict.success;
    overrideLimitationVisible = builtins.length forced == 1;
    agreement = (compare [ r second ]).status == "reported-agreement";
    agreementIsNotAuthentication = !(compare [ r second ]).canonical;
    samePathDifferentBytesHeld = (compare [ r changed ]).status == "held";
    duplicateBuilderHeld = (compare [ r r ]).status == "held";
    emptyHeld = (compare []).status == "held";
    malformedHeld = (compare [ {} {} ]).status == "held";
    differentDerivationHeld = (compare [ r (second // {
      drvPath = "/nix/store/22222222222222222222222222222222-other.drv";
    }) ]).status == "held";
  };
in assert builtins.all (x: x) (builtins.attrValues cases); cases
