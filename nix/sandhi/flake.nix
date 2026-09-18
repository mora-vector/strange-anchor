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
    in {
      nixosModules.default = import ./modules;
      lib = {
        prakrtibhava = import ./lib/prakrtibhava.nix { lib = nixpkgs.lib; };
        saksya = import ./lib/saksya.nix { lib = nixpkgs.lib; };
        mesh = import ./examples/mesh.nix;
        inherit evalTests integrationTests contractTests featureTests;
      };
      checks.${system} = {
      recovery = import ./tests/recovery.nix { inherit pkgs; };
      reachability = import ./tests/reachability.nix { inherit pkgs; };
      evaluation = pkgs.runCommand "sandhi-evaluation" {} ''
        cat > "$out" <<'JSON'
        ${builtins.toJSON { inherit evalTests integrationTests contractTests featureTests; }}
        JSON
      '';
      };
    };
}
