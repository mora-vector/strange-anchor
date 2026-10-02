# Compare reported output bytes. This function does NOT authenticate a report
# or establish that two builders actually performed independent builds.
{ lib }:
reports:
let
  validOutput = o:
    builtins.isAttrs o
    && builtins.isString (o.path or null)
    && builtins.match "/nix/store/[0-9a-z]{32}-[^/]+" o.path != null
    && builtins.isString (o.narHash or null)
    && builtins.match "sha256-[A-Za-z0-9+/]{43}=" o.narHash != null;
  validReport = r:
    builtins.isAttrs r
    && builtins.isString (r.builderId or null) && r.builderId != ""
    && builtins.isString (r.drvPath or null)
    && builtins.match "/nix/store/[0-9a-z]{32}-[^/]+[.]drv" r.drvPath != null
    && builtins.isList (r.outputs or null) && r.outputs != []
    && builtins.all validOutput r.outputs
    && builtins.length (lib.unique (map (o: o.path) r.outputs))
       == builtins.length r.outputs;
  shapeOK = builtins.isList reports && builtins.all validReport reports;
  ids = if shapeOK then map (r: r.builderId) reports else [];
  enough = shapeOK && builtins.length reports >= 2;
  distinct = builtins.length (lib.unique ids) == builtins.length ids;
  normalize = r: {
    inherit (r) drvPath;
    outputs = builtins.sort (a: b: a.path < b.path)
      (map (o: { inherit (o) path narHash; }) r.outputs);
  };
  equal = enough && builtins.all
    (r: normalize r == normalize (builtins.head reports)) reports;
in {
  status = if enough && distinct && equal then "reported-agreement" else "held";
  canonical = false; # Promotion belongs to an authenticated release pipeline.
  reasons = lib.optional (!shapeOK) "malformed-report"
    ++ lib.optional (!enough) "fewer-than-two-valid-reports"
    ++ lib.optional (!distinct) "duplicate-builder-identity"
    ++ lib.optional (enough && !equal) "derivation-or-output-mismatch";
  pending = [ "authenticate-reports" "verify-builder-independence"
    "verify-complete-output-inventory" "apply-release-policy" ];
}
