# Preserve surviving module definitions, not priority-discarded definitions.
# Documentary claims only: never use this merge for permissions or ports.
{ lib }:
elementType:
lib.mkOptionType {
  name = "prakrtibhava";
  description = "origin-bearing, uncombined ${elementType.description} claims";
  check = elementType.check;
  merge = _loc: defs:
    map (d: { source = d.file; claim = d.value; }) defs;
}
