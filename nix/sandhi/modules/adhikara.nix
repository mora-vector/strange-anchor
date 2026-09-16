# First runtime contract: local workers with private networks and owned state.
# Network adapters and inter-worker grants are intentionally not implemented.
{ config, lib, utils, ... }:
{
  options.sandhi.workers = lib.mkOption {
    default = {};
    type = lib.types.attrsOf (lib.types.submodule {
      options = {
        package = lib.mkOption { type = lib.types.package; };
        arguments = lib.mkOption { type = lib.types.listOf lib.types.str; default = []; };
        memoryMax = lib.mkOption { type = lib.types.str; default = "512M"; };
        runtimeMaxSec = lib.mkOption { type = lib.types.ints.positive; default = 300; };
      };
    });
    description = "Local workers; keys must be short lowercase service identifiers.";
  };
  config = lib.mkIf config.sandhi.enable {
    assertions = lib.mapAttrsToList (name: _: {
      assertion = builtins.match "[a-z][a-z0-9-]{0,31}" name != null;
      message = "Sandhi worker name '${name}' is not a valid local identifier.";
    }) config.sandhi.workers;
    systemd.services = lib.mapAttrs' (name: worker:
      lib.nameValuePair "sandhi-${name}" {
        description = "Sandhi local worker ${name}";
        wantedBy = [ "multi-user.target" ];
        startLimitIntervalSec = 300;
        startLimitBurst = 3;
        serviceConfig = {
          ExecStart = utils.escapeSystemdExecArgs
            ([ (lib.getExe worker.package) ] ++ worker.arguments);
          DynamicUser = true;
          StateDirectory = "sandhi-${name}";
          WorkingDirectory = "/var/lib/sandhi-${name}";
          UMask = "0077";
          PrivateNetwork = true;
          PrivateTmp = true;
          PrivateDevices = true;
          ProtectSystem = "strict";
          ProtectHome = true;
          NoNewPrivileges = true;
          CapabilityBoundingSet = "";
          RestrictAddressFamilies = [ "AF_UNIX" ];
          MemoryMax = worker.memoryMax;
          RuntimeMaxSec = worker.runtimeMaxSec;
          Restart = "on-failure";
          RestartSec = 10;
        };
      }) config.sandhi.workers;
  };
}
