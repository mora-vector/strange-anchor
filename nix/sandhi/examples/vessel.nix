{ pkgs, ... }:
{
  imports = [ ../modules ];
  sandhi = {
    enable = true;
    claims.architecture = "Sanskrit supplies design vocabulary; Nix supplies executable semantics.";
    gaps.mycelium = {
      status = "withheld";
      reason = "No introspection or executable service is specified.";
    };
    # Example only: replace with the actual archival package/source set.
    retainedPackages = [ pkgs.hello ];
  };
}
