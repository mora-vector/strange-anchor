{ config, lib, pkgs, ... }:
{
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
          }; });
          default = [];
          description = "Evidence references, not inferred from knowledge or availability.";
        };
        reason = lib.mkOption { type = lib.types.str; };
        blocksActivation = lib.mkOption { type = lib.types.bool; default = false; };
      };
    });
    default = {};
    description = "Public unresolved requirements, separate from store retention.";
  };
  config = lib.mkIf config.sandhi.enable {
    assertions = lib.mapAttrsToList (id: gap: {
      assertion = !gap.blocksActivation;
      message = "Sandhi unresolved prerequisite '${id}': ${gap.reason}";
    }) config.sandhi.gaps;
    environment.etc."sandhi/lopa.json".source =
      pkgs.writeText "sandhi-lopa.json" (builtins.toJSON config.sandhi.gaps);
  };
}
