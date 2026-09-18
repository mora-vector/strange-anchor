{ config, lib, ... }:
{
  options.sandhi = {
    enable = lib.mkEnableOption "the Sandhi substrate policy (default for each feature control)";
    services.enable = lib.mkOption {
      type = lib.types.bool;
      default = config.sandhi.enable;
      defaultText = lib.literalExpression "config.sandhi.enable";
      description = "Compile contracts and legacy workers into restricted services; false emits no Sandhi-managed workloads.";
    };
    retention.enable = lib.mkOption {
      type = lib.types.bool;
      default = config.sandhi.enable;
      defaultText = lib.literalExpression "config.sandhi.enable";
      description = "Apply recipe/output retention and the default GC policy; false leaves host retention policy untouched and deletes nothing.";
    };
    registry.export = lib.mkOption {
      type = lib.types.bool;
      default = config.sandhi.enable;
      defaultText = lib.literalExpression "config.sandhi.enable";
      description = "Export claims, gaps, and enabled service-contract snapshots; blocking gaps remain assertions even when export is false.";
    };
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
