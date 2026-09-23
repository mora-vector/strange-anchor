{ nixpkgs, system }:
let
  cfg = (nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ ../modules {
      system.stateVersion = "26.05";
      sandhi.registry.export = true;
      sandhi.gaps.example = {
        status = "unknown"; reason = "No independent builder report.";
        recoveryEvidence = [{ kind = "retained-bytes"; reference = "fixture:one"; }];
      };
    } ];
  }).config;
  snapshot = builtins.fromJSON cfg.environment.etc."sandhi/lopa-v1.json".text;
  cases = {
    versionPinned = snapshot.schemaVersion == "1.0";
    schemaNamed = snapshot.schema == "sandhi.lopa";
    unknownOriginExplicit = snapshot.provenance == { sourceRevision = null; recorder = null; };
    gapOriginExplicit = snapshot.gaps.example.provenance.assertedBy == null;
    referenceIsNotVerified = !((builtins.head snapshot.gaps.example.recoveryEvidence) ? verified);
    evidenceOriginExplicit = (builtins.head snapshot.gaps.example.recoveryEvidence).provenance.sha256 == null;
    legacyStillEmitted = cfg.environment.etc ? "sandhi/lopa.json";
  };
in assert builtins.all (x: x) (builtins.attrValues cases); {
  inherit cases;
  versioned = cfg.environment.etc."sandhi/lopa-v1.json".text;
  legacy = cfg.environment.etc."sandhi/lopa.json".source;
}
