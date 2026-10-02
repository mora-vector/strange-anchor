{
  description = "Sandhi: provenance-bearing NixOS shards, pre-deployment prototype";
  inputs.nixpkgs.url = "https://releases.nixos.org/nixos/26.05/nixos-26.05.9843.b67c7a60c373/nixexprs.tar.xz";
  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      evalTests = import ./tests/eval.nix { lib = nixpkgs.lib; };
      contractTests = import ./tests/contracts.nix { inherit nixpkgs system; };
      integrationTests = import ./tests/integration.nix { inherit nixpkgs system; };
      featureTests = import ./tests/features.nix { inherit nixpkgs system; };
      exportFixture = import ./tests/export.nix { inherit nixpkgs system; };
      exportTests = exportFixture.cases;
      python = pkgs.python3.withPackages (p: [ p.jsonschema ]);
      source = nixpkgs.lib.cleanSourceWith {
        src = ./.;
        filter = path: type: !(builtins.elem (baseNameOf path)
          [ "evidence" "docs" "README.md" "VALIDATION.json" "__pycache__" ]);
      };
    in {
      nixosModules.default = import ./modules;
      lib = {
        prakrtibhava = import ./lib/prakrtibhava.nix { lib = nixpkgs.lib; };
        saksya = import ./lib/saksya.nix { lib = nixpkgs.lib; };
        mesh = import ./examples/mesh.nix;
        inherit evalTests integrationTests contractTests featureTests exportTests;
      };
      packages.${system}.lopa-audit = import ./packages/lopa-audit.nix { inherit pkgs; };
      checks.${system} = {
      applicability = import ./tests/applicability.nix { inherit pkgs; };
      budgets = import ./tests/budgets.nix { inherit pkgs; };
      workload = import ./tests/workload.nix { inherit pkgs; };
      recovery = import ./tests/recovery.nix { inherit pkgs; };
      reachability = import ./tests/reachability.nix { inherit pkgs; };
      evaluation = pkgs.runCommand "sandhi-evaluation" { nativeBuildInputs = [ python ]; } ''
        export PYTHONDONTWRITEBYTECODE=1
        python -m unittest discover -s ${source}/tests -p 'test_*.py' -v
        python ${source}/scripts/lopa_audit.py --schema ${./schemas/lopa-v1.schema.json} ${pkgs.writeText "lopa-v1-fixture.json" exportFixture.versioned} > audit.json
        python ${source}/scripts/lopa_audit.py --schema ${./schemas/lopa-v2.schema.json} ${exportFixture.versionedV2} > audit-v2.json
        python - ${exportFixture.legacy} <<'PY'
        import json, sys
        with open(sys.argv[1]) as f:
            actual = json.load(f)
        assert actual == {"example": {"status": "unknown", "availability": "unassessed",
            "reason": "No independent builder report.", "blocksActivation": False,
            "recoveryEvidence": [{"kind": "retained-bytes", "reference": "fixture:one"}]}}, actual
        PY
        cat > "$out" <<'JSON'
        ${builtins.toJSON { inherit evalTests integrationTests contractTests featureTests exportTests; }}
        JSON
      '';
      };
    };
}
