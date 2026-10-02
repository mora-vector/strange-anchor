{ config, lib, pkgs, ... }:
let
  provenance = lib.types.submodule { options = {
    sourceReference = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    assertedBy = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    recordedAt = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    sha256 = lib.mkOption {
      type = lib.types.nullOr (lib.types.strMatching "[0-9a-f]{64}"); default = null;
      description = "Declared digest of referenced bytes; not verification or authentication.";
    };
  }; };
  # Freeze the original shape even when the typed declarations gain fields.
  legacy = lib.mapAttrs (_: gap: {
    inherit (gap) status availability reason blocksActivation;
    recoveryEvidence = map (e: { inherit (e) kind reference; }) gap.recoveryEvidence;
  }) config.sandhi.gaps;
  manager = import ../packages/recovery-state.nix { inherit pkgs policyFile; };
  snapshot = {
    schema = "sandhi.lopa";
    schemaVersion = "1.0";
    provenance = config.sandhi.registry.provenance;
    gaps = config.sandhi.gaps;
  };
  snapshotV2 = snapshot // {
    schemaVersion = "2.0";
    evidenceSemantics = "historical-declarations";
    # Declared targets and the configured premise, kept even when retention is
    # off; not an observed rooted inventory or evidence of recoverability.
    recoveryPolicy = {
      retentionEnabled = config.sandhi.retention.enable;
      subjects = map (p: { kind = "output"; path = builtins.unsafeDiscardStringContext (toString p); }) config.sandhi.retainedPackages
        ++ map (p: { kind = "recipe"; path = builtins.unsafeDiscardStringContext p.drvPath; }) config.sandhi.retainedRecipes;
    };
  };
  policyFile = pkgs.writeText "sandhi-lopa-v2.json" (builtins.toJSON snapshotV2);
in {
  options.sandhi.registry.provenance = lib.mkOption {
    type = lib.types.submodule { options = {
      sourceRevision = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
      recorder = lib.mkOption { type = lib.types.nullOr lib.types.str; default = null; };
    }; };
    default = {};
    description = "Operator-declared source identity; unknowns stay null. No impure clock or inferred attestation.";
  };
  options.sandhi.gaps = lib.mkOption {
    type = lib.types.attrsOf (lib.types.submodule {
      options = {
        status = lib.mkOption {
          type = lib.types.enum [ "unknown" "withheld" "unsupported" "inapplicable" ];
        };
        availability = lib.mkOption {
          type = lib.types.enum [ "unassessed" "present" "absent" "unreachable" ];
          default = "unassessed";
        };
        recoveryEvidence = lib.mkOption {
          type = lib.types.listOf (lib.types.submodule { options = {
            kind = lib.mkOption { type = lib.types.enum
              [ "retained-bytes" "retained-recipe-and-inputs" "verified-restoration" ]; };
            reference = lib.mkOption { type = lib.types.str; };
            provenance = lib.mkOption { type = provenance; default = {}; };
          }; });
          default = [];
          description = "Evidence references, not inferred from knowledge or availability.";
        };
        reason = lib.mkOption { type = lib.types.str; };
        provenance = lib.mkOption { type = provenance; default = {}; };
        blocksActivation = lib.mkOption { type = lib.types.bool; default = false; };
      };
    });
    default = {};
    description = "Public unresolved requirements, separate from store retention.";
  };
  config = {
    environment.systemPackages = [ manager ];
    # Bookkeeping must also run when retention/export are disabled. Every
    # activation withdraws current claims, including switching back to an old
    # system closure. Immutable snapshots alone cannot remember an off/on cycle.
    system.activationScripts.sandhiRecovery = {
      deps = [ "var" ];
      text = "${manager}/bin/sandhi-recovery-state activate ${policyFile} >/dev/null";
    };
    # A declared blocker is a prerequisite, not a visibility preference. Even
    # disabling every Sandhi feature must not silently resolve it.
    assertions = lib.mapAttrsToList (id: gap: {
      assertion = !gap.blocksActivation;
      message = "Sandhi unresolved prerequisite '${id}': ${gap.reason}";
    }) config.sandhi.gaps;
    environment.etc = lib.mkIf config.sandhi.registry.export {
      "sandhi/lopa.json".source =
        pkgs.writeText "sandhi-lopa.json" (builtins.toJSON legacy);
      "sandhi/lopa-v1.json".text = builtins.toJSON snapshot;
      "sandhi/lopa-v2.json".source = policyFile;
    };
  };
}
