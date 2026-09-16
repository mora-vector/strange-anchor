{ config, lib, ... }:
{
  config = lib.mkIf config.sandhi.enable {
    nix.settings = {
      keep-derivations = true;
      keep-outputs = lib.mkIf (config.sandhi.retainedRecipes != []) true;
      sandbox = true;
      require-sigs = true;
      allow-import-from-derivation = false;
    };
    # A conservative first cut: no scheduled GC. Manual root actions remain
    # administrative operations; this does not prohibit root from deleting.
    nix.gc.automatic = lib.mkDefault false;
    system.extraDependencies = config.sandhi.retainedPackages
      ++ map (drv: drv.drvPath) config.sandhi.retainedRecipes;
  };
}
