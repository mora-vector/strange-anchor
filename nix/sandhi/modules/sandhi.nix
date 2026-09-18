{ config, lib, pkgs, ... }:
let
  prakrtibhava = import ../lib/prakrtibhava.nix { inherit lib; };
in {
  options.sandhi.claims = lib.mkOption {
    type = lib.types.attrsOf (prakrtibhava lib.types.str);
    default = {};
    description = ''Public documentary claims grouped by subject. Definitions
      remain separate with their source files, after Nix priority filtering.
      Do not put secrets here. Operational decisions use ordinary options.'';
  };
  config = lib.mkIf config.sandhi.registry.export {
    environment.etc."sandhi/claims.json".source =
      pkgs.writeText "sandhi-claims.json" (builtins.toJSON config.sandhi.claims);
  };
}
