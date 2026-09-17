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
    # drvPath normally carries a deep context that requests its outputs too.
    # Keep a constant reference to the recipe and its input reference closure;
    # selecting a recipe must not itself require a successful output build.
    system.extraDependencies = config.sandhi.retainedPackages
      ++ map (drv: builtins.unsafeDiscardOutputDependency drv.drvPath)
        config.sandhi.retainedRecipes;
  };
}
