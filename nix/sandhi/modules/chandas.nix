{ lib, ... }:
{
  options.sandhi.chandas = lib.mkOption {
    default = {};
    type = lib.types.attrsOf (lib.types.submodule { options = {
      cpuPercent = lib.mkOption { type = lib.types.ints.between 1 10000; };
      memoryMiB = lib.mkOption { type = lib.types.ints.positive; };
      retries = lib.mkOption { type = lib.types.ints.unsigned; default = 2; };
      windowSec = lib.mkOption { type = lib.types.ints.positive; default = 300; };
      runtimeMaxSec = lib.mkOption { type = lib.types.ints.positive; default = 300; };
    }; });
    description = "Required budget per contract. retries counts retries after the initial attempt.";
  };
}
