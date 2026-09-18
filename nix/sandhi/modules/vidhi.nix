{ config, lib, pkgs, utils, ... }:
let
  cfg = config.sandhi;
  names = builtins.attrNames cfg.contracts;
  validName = name: builtins.match "[a-z][a-z0-9-]{0,31}" name != null;
  # Run privileged, before the workload, in its service cgroup. Refuse startup
  # if effective ingress/egress BPF filters cannot be inspected. This establishes
  # attachment, not policy correctness; the packet-level VM test covers the latter.
  checkFilter = pkgs.writeShellScript "sandhi-require-ip-filter" ''
    set -euo pipefail
    group=$(${pkgs.gawk}/bin/awk -F: '$1 == "0" { print $3 }' /proc/self/cgroup)
    test -n "$group"
    ${pkgs.bpftools}/bin/bpftool -j cgroup show "/sys/fs/cgroup$group" effective |
      ${pkgs.jq}/bin/jq -e '
        any(.[]; .attach_type | endswith("ingress")) and
        any(.[]; .attach_type | endswith("egress"))' >/dev/null
  '';
  budget = name: cfg.chandas.${name} or {
    cpuPercent = 1; memoryMiB = 64; retries = 0; windowSec = 60; runtimeMaxSec = 10;
  };
  peerAddresses = kk: map (p: cfg.peers.${p}.ipv4)
    (builtins.filter (p: builtins.hasAttr p cfg.peers) kk.sampradana);
  sourcePackages = kk: map (p: cfg.inputs.${p})
    (builtins.filter (p: builtins.hasAttr p cfg.inputs) kk.apadana);
in {
  config = lib.mkIf cfg.services.enable {
    assertions = lib.concatMap (name:
      let kk = cfg.contracts.${name}; in [
        { assertion = validName name; message = "Sandhi invalid contract name: ${name}"; }
        { assertion = builtins.hasAttr name cfg.chandas;
          message = "Sandhi contract '${name}' has no chandas budget."; }
        { assertion = kk.adhikarana == cfg.locus;
          message = "Sandhi contract '${name}' belongs to another locus."; }
        { assertion = builtins.all (p: builtins.hasAttr p cfg.peers) kk.sampradana;
          message = "Sandhi contract '${name}' references an undeclared peer."; }
        { assertion = builtins.all (p: builtins.hasAttr p cfg.inputs) kk.apadana;
          message = "Sandhi contract '${name}' references an undeclared input."; }
      ]) names ++ [
      { assertion = builtins.length (lib.unique (map (n: cfg.contracts.${n}.kartr) names)) == builtins.length names;
        message = "Sandhi contracts must have distinct runtime agents."; }
      { assertion = builtins.length (lib.unique (map (n: cfg.contracts.${n}.karman.state) names)) == builtins.length names;
        message = "Sandhi contracts must have distinct state directories."; }
    ];
    system.extraDependencies = lib.concatMap (n: sourcePackages cfg.contracts.${n}) names;
    environment.etc = lib.mkIf cfg.registry.export {
      "sandhi/contracts.json".text = builtins.toJSON {
        inherit (cfg) locus peers contracts chandas;
      };
    };
    systemd.services = lib.mapAttrs' (name: kk:
      let c = budget name; in lib.nameValuePair "sandhi-contract-${name}" {
        description = "Sandhi contract ${name}";
        wantedBy = lib.optional kk.startAtBoot "multi-user.target";
        startLimitIntervalSec = c.windowSec;
        startLimitBurst = c.retries + 1;
        serviceConfig = {
          ExecStart = utils.escapeSystemdExecArgs ([ (lib.getExe kk.karana) ] ++ kk.arguments);
          ExecStartPre = lib.optional (kk.sampradana != []) "+${checkFilter}";
          DynamicUser = true;
          User = "sc-${kk.kartr}";
          StateDirectory = "sandhi-contract-${kk.karman.state}";
          WorkingDirectory = "/var/lib/sandhi-contract-${kk.karman.state}";
          ReadOnlyPaths = kk.karman.affected;
          ProtectSystem = "strict";
          ProtectHome = true;
          PrivateTmp = true;
          PrivateDevices = true;
          NoNewPrivileges = true;
          CapabilityBoundingSet = "";
          RestrictSUIDSGID = true;
          RestrictNamespaces = true;
          UMask = "0077";
          PrivateNetwork = kk.sampradana == [];
          RestrictAddressFamilies = if kk.sampradana == [] then [ "AF_UNIX" ]
            else [ "AF_UNIX" "AF_INET" ];
          IPAddressDeny = "any";
          IPAddressAllow = peerAddresses kk;
          CPUQuota = "${toString c.cpuPercent}%";
          MemoryMax = "${toString c.memoryMiB}M";
          RuntimeMaxSec = c.runtimeMaxSec;
          Restart = "on-failure";
          RestartSec = 2;
        };
      }) cfg.contracts;
  };
}
