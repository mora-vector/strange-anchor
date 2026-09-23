{ nixpkgs, system }:
let
  lib = nixpkgs.lib;
  mk = features: extra: (lib.nixosSystem {
    inherit system;
    modules = [ ../modules ({ pkgs, ... }: {
      system.stateVersion = "26.05";
      # Deliberately different host defaults reveal accidental policy leakage.
      nix.settings = {
        keep-derivations = lib.mkDefault false;
        keep-outputs = lib.mkDefault false;
        sandbox = lib.mkDefault false;
        require-sigs = lib.mkDefault false;
        allow-import-from-derivation = lib.mkDefault true;
      };
      nix.gc.automatic = lib.mkOverride 1100 true;
      sandhi = {
        enable = false;
        inputs.reference = pkgs.writeText "sandhi-runtime-input" "runtime";
        retainedPackages = [ (pkgs.writeText "sandhi-retained-output" "retained") ];
        retainedRecipes = [ (pkgs.writeText "sandhi-retained-recipe" "recipe") ];
        workers.legacy.package = pkgs.hello;
        contracts.probe = {
          karana = pkgs.hello; adhikarana = "backplane";
          apadana = [ "reference" ];
        };
        chandas.probe = { cpuPercent = 50; memoryMiB = 128; };
        gaps.prerequisite = {
          status = "unknown"; reason = "A declared prerequisite.";
          blocksActivation = true;
        };
      } // features;
    }) extra ];
  }).config;
  failures = cfg: builtins.filter
    (a: !a.assertion && lib.hasPrefix "Sandhi" a.message) cfg.assertions;
  check = { services, retention, export, umbrella ? false }: cfg:
    let
      security = umbrella || services || retention;
      present = path: builtins.elem path cfg.system.extraDependencies;
    in {
      contractUnit = (cfg.systemd.services ? sandhi-contract-probe) == services;
      legacyUnit = (cfg.systemd.services ? sandhi-legacy) == services;
      serviceRestrictions = !services || (
        cfg.systemd.services.sandhi-contract-probe.serviceConfig.PrivateNetwork
        && cfg.systemd.services.sandhi-contract-probe.serviceConfig.ProtectSystem == "strict"
        && cfg.systemd.services.sandhi-legacy.serviceConfig.PrivateNetwork);
      runtimeDependency = present cfg.sandhi.inputs.reference == services;
      selectedOutput = present (builtins.head cfg.sandhi.retainedPackages) == retention;
      selectedRecipe = present (builtins.head cfg.sandhi.retainedRecipes).drvPath == retention;
      keepDerivations = cfg.nix.settings.keep-derivations == retention;
      keepOutputs = cfg.nix.settings.keep-outputs == retention;
      gcPolicy = cfg.nix.gc.automatic == !retention;
      buildSecurity = cfg.nix.settings.sandbox == security
        && cfg.nix.settings.require-sigs == security
        && cfg.nix.settings.allow-import-from-derivation == !security;
      claimsExport = (cfg.environment.etc ? "sandhi/claims.json") == export;
      gapExport = (cfg.environment.etc ? "sandhi/lopa.json") == export;
      versionedGapExport = (cfg.environment.etc ? "sandhi/lopa-v1.json") == export;
      activeContractExport = (cfg.environment.etc ? "sandhi/contracts.json") == (export && services);
      blockingGap = builtins.any (a: a.message ==
        "Sandhi unresolved prerequisite 'prerequisite': A declared prerequisite.") (failures cfg);
    };
  booleans = [ false true ];
  combinations = lib.concatMap (services:
    lib.concatMap (retention:
      map (export: { inherit services retention export; }) booleans) booleans) booleans;
  bit = b: if b then "1" else "0";
  matrix = lib.foldl' (acc: flags:
    acc // lib.mapAttrs' (name: value:
      lib.nameValuePair "s${bit flags.services}r${bit flags.retention}e${bit flags.export}-${name}" value)
      (check flags (mk {
        services.enable = flags.services;
        retention.enable = flags.retention;
        registry.export = flags.export;
      } {}))) {} combinations;
  umbrella = check { services = true; retention = true; export = true; umbrella = true; }
    (mk { enable = true; } {});
  overridden = check { services = false; retention = false; export = false; umbrella = true; }
    (mk { enable = true; services.enable = false; retention.enable = false; registry.export = false; } {});
  invalid = services: mk { services.enable = services; registry.export = false; }
    { sandhi.contracts.probe.sampradana = [ "undeclared" ]; };
  cases = matrix
    // lib.mapAttrs' (n: v: lib.nameValuePair "umbrella-${n}" v) umbrella
    // lib.mapAttrs' (n: v: lib.nameValuePair "explicitOff-${n}" v) overridden
    // {
      exportOffStillValidatesContracts = builtins.any (a: a.message ==
        "Sandhi contract 'probe' references an undeclared peer.") (failures (invalid true));
      dormantContractEmitsNoUnit = !((invalid false).systemd.services ? sandhi-contract-probe);
      dormantContractHasOnlyDeclaredGapBlocker = builtins.length (failures (invalid false)) == 1;
    };
in assert builtins.all (x: x) (builtins.attrValues cases); cases
