{ pkgs }:
let python = pkgs.python3.withPackages (p: [ p.jsonschema ]);
in pkgs.writeShellApplication {
  name = "sandhi-lopa-audit";
  text = ''
    exec ${python}/bin/python3 ${../scripts/lopa_audit.py} --schema ${../schemas/lopa-v1.schema.json} "$@"
  '';
}
