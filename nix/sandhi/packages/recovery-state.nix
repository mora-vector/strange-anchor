{ pkgs, policyFile ? null }:
pkgs.writeShellApplication {
  name = "sandhi-recovery-state";
  text = ''
    exec ${pkgs.python3}/bin/python3 ${../scripts/recovery_state.py} ${pkgs.lib.optionalString (policyFile != null) "--policy ${policyFile}"} "$@"
  '';
}
