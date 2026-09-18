{ lib, ... }:
let
  t = lib.types;
  identifier = t.strMatching "[a-z][a-z0-9-]{0,31}";
  absolute = t.strMatching "/[A-Za-z0-9/_.-]+";
  ipv4 = t.addCheck t.str (s:
    builtins.match "[0-9]+[.][0-9]+[.][0-9]+[.][0-9]+" s != null
    && builtins.all (part: builtins.stringLength part <= 3
      && (part == "0" || !lib.hasPrefix "0" part)
      && lib.toInt part <= 255) (lib.splitString "." s));
in {
  options.sandhi = {
    locus = lib.mkOption { type = identifier; default = "backplane"; };
    peers = lib.mkOption {
      type = t.attrsOf (t.submodule { options.ipv4 = lib.mkOption { type = ipv4; }; });
      default = {};
      description = "Explicit IPv4 endpoints; address grants do not authenticate identities or restrict ports.";
    };
    inputs = lib.mkOption { type = t.attrsOf t.package; default = {}; };
    contracts = lib.mkOption {
      default = {};
      type = t.attrsOf (t.submodule ({ name, ... }: { options = {
        kartr = lib.mkOption { type = t.strMatching "[a-z][a-z0-9-]{0,27}"; default = name; };
        karman = {
          state = lib.mkOption {
            type = identifier; default = name;
            description = "Owned writable state under /var/lib/sandhi-contract-<state>; not an arbitrary host write grant.";
          };
          affected = lib.mkOption {
            type = t.listOf absolute; default = [];
            description = ''Required host paths bound read-only by systemd.
              Missing bind sources prevent service startup. These are not write grants
              or a complete read allowlist; ordinary permissions still apply.
              Existence is checked on the runtime host, not by Nix evaluation.'';
          };
        };
        karana = lib.mkOption { type = t.package; };
        arguments = lib.mkOption { type = t.listOf t.str; default = []; };
        sampradana = lib.mkOption { type = t.listOf identifier; default = []; };
        apadana = lib.mkOption { type = t.listOf identifier; default = []; };
        adhikarana = lib.mkOption { type = identifier; };
        startAtBoot = lib.mkOption { type = t.bool; default = true; };
      }; }));
      description = "Service contracts compiled by vidhi; all values are public configuration.";
    };
  };
}
