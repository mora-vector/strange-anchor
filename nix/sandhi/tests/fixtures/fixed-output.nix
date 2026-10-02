# Minimal fixture; this file can also be instantiated inside the test guest.
{ name, url, sha256 }:
builtins.derivation {
  inherit name url;
  system = "builtin";
  builder = "builtin:fetchurl";
  outputHashAlgo = "sha256";
  outputHashMode = "flat";
  outputHash = sha256;
  executable = false;
  unpack = false;
  preferLocalBuild = true;
  allowSubstitutes = false;
}
