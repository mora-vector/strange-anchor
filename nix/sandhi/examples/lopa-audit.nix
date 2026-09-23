{ pkgs, config, ... }:
let
  audit = import ../packages/lopa-audit.nix { inherit pkgs; };
  runner = pkgs.writeShellApplication {
    name = "sandhi-audit-local-snapshot";
    text = ''
      # Publish a report only after validation, in the contract's owned state.
      ${audit}/bin/sandhi-lopa-audit /etc/sandhi/lopa-v1.json > report.json.tmp
      mv report.json.tmp report.json
    '';
  };
in {
  imports = [ ../modules ];
  sandhi = {
    services.enable = true;
    registry.export = true;
    contracts.lopa-audit = {
      karana = runner; adhikarana = config.sandhi.locus;
      karman.affected = [ "/etc/sandhi/lopa-v1.json" ];
      sampradana = []; startAtBoot = false;
    };
    chandas.lopa-audit = {
      cpuPercent = 50; memoryMiB = 128; runtimeMaxSec = 30;
      retries = 0; windowSec = 300;
    };
  };
}
