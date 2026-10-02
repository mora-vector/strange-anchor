{ config, lib, ... }:
let cfg = config.sandhi;
in
{
  config = lib.mkMerge [ (lib.mkIf (cfg.enable || cfg.services.enable || cfg.retention.enable) {
    nix.settings = {
      sandbox = true;
      require-sigs = true;
      allow-import-from-derivation = false;
    };
  }) (lib.mkIf cfg.retention.enable {
    nix.settings = {
      keep-derivations = true;
      keep-outputs = lib.mkIf (config.sandhi.retainedRecipes != []) true;
    };
    # A conservative first cut: no scheduled GC. Manual root actions remain
    # administrative operations; this does not prohibit root from deleting.
    nix.gc.automatic = lib.mkDefault false;
    # drvPath normally carries a deep context that requests its outputs too.
    # Keep a constant reference to the recipe and its input reference closure;
    # selecting a recipe must not itself require a successful output build.
    system.extraDependencies = config.sandhi.retainedPackages
      ++ map (drv: builtins.unsafeDiscardOutputDependency drv.drvPath)
        config.sandhi.retainedRecipes;
  }) ];
}
