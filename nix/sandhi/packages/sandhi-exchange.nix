# Stage A exchange programs (DECISIONS.md 2026-10-05). Python standard library only.
# The node is the contract executable; the responder and probe are separate tools.
{ pkgs }:
pkgs.runCommand "sandhi-exchange" { meta.mainProgram = "sandhi-exchange-node"; } ''
  mkdir -p $out/lib/sandhi-exchange $out/bin
  cp ${../scripts/exchange_protocol.py} $out/lib/sandhi-exchange/exchange_protocol.py
  cp ${../scripts/exchange_node.py} $out/lib/sandhi-exchange/exchange_node.py
  cp ${../scripts/exchange_responder.py} $out/lib/sandhi-exchange/exchange_responder.py
  cp ${../scripts/exchange_probe.py} $out/lib/sandhi-exchange/exchange_probe.py
  for tool in node responder probe; do
    cat > $out/bin/sandhi-exchange-$tool <<EOF
  #!${pkgs.runtimeShell}
  exec ${pkgs.python3}/bin/python3 -I $out/lib/sandhi-exchange/exchange_$tool.py "\$@"
  EOF
    chmod +x $out/bin/sandhi-exchange-$tool
  done
''
