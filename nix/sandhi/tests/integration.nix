{ nixpkgs, system }:
let
  vessel = nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ ../examples/vessel.nix { system.stateVersion = "26.05"; } ];
  };
  cfg = vessel.config;
  blocked = nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ ../examples/vessel.nix {
      system.stateVersion = "26.05";
      sandhi.gaps.hardware = {
        status = "unknown";
        reason = "Hardware configuration is not supplied.";
        blocksActivation = true;
      };
    } ];
  };
  workerHost = nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [ ../examples/vessel.nix ({ pkgs, ... }: {
      system.stateVersion = "26.05";
      sandhi.workers.probe.package = pkgs.hello;
    }) ];
  };
  worker = workerHost.config.systemd.services.sandhi-probe;
  cases = {
    workerIsNetworkIsolated = worker.serviceConfig.PrivateNetwork;
    workerHasBoundedRestarts = worker.startLimitBurst == 3;
    workerUsesPackagedCommand = nixpkgs.lib.hasInfix "/bin/hello" worker.serviceConfig.ExecStart;
    workerOwnsState = worker.serviceConfig.StateDirectory == "sandhi-probe";
    recipesRetained = cfg.nix.settings.keep-derivations;
    noImportFromDerivation = !cfg.nix.settings.allow-import-from-derivation;
    noScheduledGC = !cfg.nix.gc.automatic;
    retainedPackageInClosure = builtins.length cfg.system.extraDependencies >= 1;
    claimsExported = cfg.environment.etc ? "sandhi/claims.json";
    gapsExported = cfg.environment.etc ? "sandhi/lopa.json";
    unknownPrerequisiteFailsAssertion = builtins.any
      (a: !a.assertion && a.message ==
        "Sandhi unresolved prerequisite 'hardware': Hardware configuration is not supplied.")
      blocked.config.assertions;
  };
in assert builtins.all (x: x) (builtins.attrValues cases); cases
