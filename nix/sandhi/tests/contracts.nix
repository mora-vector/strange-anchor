{ nixpkgs, system }:
let
  lib = nixpkgs.lib;
  mk = extra: (lib.nixosSystem {
    inherit system;
    modules = [ ../modules ({ pkgs, ... }: {
      system.stateVersion = "26.05";
      sandhi = {
        enable = true;
        peers.sideband.ipv4 = "127.0.0.2";
        inputs.reference = pkgs.hello;
        contracts.probe = {
          karana = pkgs.hello; adhikarana = "backplane";
          sampradana = [ "sideband" ]; apadana = [ "reference" ];
        };
        chandas.probe = { cpuPercent = 50; memoryMiB = 128; };
        gaps.unseen = { status = "unknown"; reason = "Unmeasured."; };
      };
    }) extra ];
  }).config;
  cfg = mk {};
  failures = c: builtins.filter (a: !a.assertion && lib.hasPrefix "Sandhi" a.message) c.assertions;
  unit = cfg.systemd.services.sandhi-contract-probe;
  missingPeer = mk { sandhi.contracts.probe.sampradana = lib.mkForce [ "unregistered" ]; };
  missingInput = mk { sandhi.contracts.probe.apadana = lib.mkForce [ "unregistered" ]; };
  missingBudget = mk { sandhi.chandas = lib.mkForce {}; };
  wrongLocus = mk { sandhi.contracts.probe.adhikarana = lib.mkForce "elsewhere"; };
  empty = mk { sandhi.contracts.probe.sampradana = lib.mkForce []; };
  retained = mk ({ pkgs, ... }: { sandhi.retainedRecipes = [ pkgs.hello ]; });
  legacyCollision = mk ({ pkgs, ... }: { sandhi.workers.contract-probe.package = pkgs.hello; });
  duplicateAgent = mk ({ pkgs, ... }: {
    sandhi.contracts.other = { kartr = "probe"; karana = pkgs.hello; adhikarana = "backplane"; };
    sandhi.chandas.other = { cpuPercent = 50; memoryMiB = 128; };
  });
  duplicateState = mk ({ pkgs, ... }: {
    sandhi.contracts.other = { karman.state = "probe"; karana = pkgs.hello; adhikarana = "backplane"; };
    sandhi.chandas.other = { cpuPercent = 50; memoryMiB = 128; };
  });
  cases = {
    legacyWorkerCannotClaimContractUnit = builtins.any
      (a: a.message == "Sandhi worker 'contract-probe' uses the reserved contract- namespace.")
      (failures legacyCollision);
    duplicateAgentBlocked = builtins.any
      (a: a.message == "Sandhi contracts must have distinct runtime agents.")
      (failures duplicateAgent);
    duplicateStateBlocked = builtins.any
      (a: a.message == "Sandhi contracts must have distinct state directories.")
      (failures duplicateState);
    selectedRecipeInSystemClosure = builtins.elem
      (builtins.head retained.sandhi.retainedRecipes).drvPath retained.system.extraDependencies;
    selectedRecipeEnablesOutputRetention = retained.nix.settings.keep-outputs;
    validContractAccepted = failures cfg == [];
    missingPeerBlocked = failures missingPeer != [];
    missingInputBlocked = failures missingInput != [];
    missingBudgetBlocked = failures missingBudget != [];
    wrongLocusBlocked = failures wrongLocus != [];
    nonemptyPeersUseAddressFilter = !unit.serviceConfig.PrivateNetwork
      && unit.serviceConfig.IPAddressAllow == [ "127.0.0.2" ];
    nonemptyPeersRequireFilterInspection = unit.serviceConfig.ExecStartPre != [];
    emptyRecipientsUsePrivateNetwork = empty.systemd.services.sandhi-contract-probe.serviceConfig.PrivateNetwork;
    retriesIncludeInitialAttempt = unit.startLimitBurst == 3;
    unknownNeedsNoRecoveryClaim = cfg.sandhi.gaps.unseen.recoveryEvidence == []
      && cfg.sandhi.gaps.unseen.availability == "unassessed";
  };
in assert builtins.all (x: x) (builtins.attrValues cases); cases
