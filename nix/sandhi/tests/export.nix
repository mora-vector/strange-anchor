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
  # A pair differing only in retention, holding a historical restoration claim.
  paired = retention: (nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ ../modules ({ pkgs, ... }: {
      system.stateVersion = "26.05";
      sandhi.retention.enable = retention;
      sandhi.registry.export = true;
      sandhi.retainedPackages = [ (pkgs.writeText "sandhi-paired-subject" "fixture\n") ];
      sandhi.gaps.restored = {
        status = "unknown"; reason = "Paired retention fixture.";
        recoveryEvidence = [{ kind = "verified-restoration"; reference = "fixture:historical-restoration"; }];
      };
    }) ];
  }).config.environment.etc;
  on = paired true;
  off = paired false;
  snapshot = builtins.fromJSON cfg.environment.etc."sandhi/lopa-v1.json".text;
  cases = {
    versionPinned = snapshot.schemaVersion == "1.0";
    schemaNamed = snapshot.schema == "sandhi.lopa";
    unknownOriginExplicit = snapshot.provenance == { sourceRevision = null; recorder = null; };
    gapOriginExplicit = snapshot.gaps.example.provenance.assertedBy == null;
    referenceIsNotVerified = !((builtins.head snapshot.gaps.example.recoveryEvidence) ? verified);
    evidenceOriginExplicit = (builtins.head snapshot.gaps.example.recoveryEvidence).provenance.sha256 == null;
    v2Emitted = cfg.environment.etc ? "sandhi/lopa-v2.json";
    lifecycleSurvivesDisabledRetention = cfg.system.activationScripts ? sandhiRecovery;
    legacyStillEmitted = cfg.environment.etc ? "sandhi/lopa.json";
    # Legacy and 1.0 never express current recoverability, so retention cannot
    # change their bytes; identical writeText paths imply identical contents.
    legacyRetentionInvariant = on."sandhi/lopa.json".source == off."sandhi/lopa.json".source;
    v1RetentionInvariant = on."sandhi/lopa-v1.json".text == off."sandhi/lopa-v1.json".text;
    v2RecordsRetentionPremise = on."sandhi/lopa-v2.json".source != off."sandhi/lopa-v2.json".source;
  };
in assert builtins.all (x: x) (builtins.attrValues cases); {
  inherit cases;
  versioned = cfg.environment.etc."sandhi/lopa-v1.json".text;
  versionedV2 = cfg.environment.etc."sandhi/lopa-v2.json".source;
  legacy = cfg.environment.etc."sandhi/lopa.json".source;
  pairedV2 = { on = on."sandhi/lopa-v2.json".source; off = off."sandhi/lopa-v2.json".source; };
}
