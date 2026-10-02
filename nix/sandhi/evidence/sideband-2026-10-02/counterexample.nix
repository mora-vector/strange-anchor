# Sideband probe, 2026-10-02. Not a flake check and not a recovery test.
# Question: with export on, can a consumer of each Lopa export tell retention
# on from retention off when a gap carries a historical restoration claim?
# Run from the repository root:
#   nix eval --impure --json -f nix/sandhi/evidence/sideband-2026-10-02/counterexample.nix
let
  flake = builtins.getFlake "path:${toString ../..}";
  nixpkgs = flake.inputs.nixpkgs;
  mk = retention: (nixpkgs.lib.nixosSystem {
    system = "x86_64-linux";
    modules = [ flake.nixosModules.default ({ pkgs, ... }: {
      system.stateVersion = "26.05";
      boot.loader.grub.enable = false;
      fileSystems."/" = { device = "none"; fsType = "tmpfs"; };
      sandhi.retention.enable = retention;
      sandhi.registry.export = true;
      sandhi.retainedPackages = [ pkgs.hello ];
      sandhi.gaps.recovery = {
        status = "unknown"; reason = "probe";
        recoveryEvidence = [{ kind = "verified-restoration"; reference = "fixture:historical-restoration"; }];
      };
    }) ];
  }).config;
  files = c: {
    legacy = builtins.readFile c.environment.etc."sandhi/lopa.json".source;
    v1 = c.environment.etc."sandhi/lopa-v1.json".text;
    v2 = builtins.readFile c.environment.etc."sandhi/lopa-v2.json".source;
  };
  on = files (mk true); off = files (mk false);
in {
  legacyIdentical = on.legacy == off.legacy;
  v1Identical = on.v1 == off.v1;
  v2Identical = on.v2 == off.v2;
  legacyOff = off.legacy;
  v2OffPolicy = (builtins.fromJSON off.v2).recoveryPolicy;
}
