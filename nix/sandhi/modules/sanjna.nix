{ lib, ... }:
{
  options.sandhi = {
    enable = lib.mkEnableOption "the Sandhi substrate policy";
    retainedRecipes = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [];
      description = "Selected derivation recipes rooted through the system closure; enables global keep-outputs retention.";
    };
    retainedPackages = lib.mkOption {
      type = lib.types.listOf lib.types.package;
      default = [];
      description = ''Packages or fetched source derivations retained through
        the system closure. Retention lasts only while a retaining generation
        remains rooted. This is not an off-host archive.'';
    };
  };
}
