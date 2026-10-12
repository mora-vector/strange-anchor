# DeviationShrineOS repository copy

The application and supporting source files were copied byte-for-byte from the published DeviationShrineOS build. `IMPORT-MANIFEST.json` records the selection and original SHA-256 checksums. Hosting-specific identity is excluded so this directory can be served independently.

## Run

From the repository root:

```sh
python3 -m http.server 8000 --directory deviationshrineos/dist
```

Then open http://localhost:8000 in a browser. No build or runtime package installation is required.

## Check

```sh
cd deviationshrineos
npm test
```

The optional simulated-DOM interaction test requires LinkeDOM 0.18.12 installed separately. Pass its absolute module path:

```sh
node tests/dom-integration.mjs /absolute/path/to/linkedom/esm/index.js
```

To regenerate the bundled font, install Python `fonttools` and run `python3 tools/build_font.py`. The bundled WOFF is already ready to serve; regeneration is optional.

## Scope

This is the browser desktop from the originating build session. It adds no NixOS package, real TempleOS VM, model runner, external communication service, or automatic deployment workflow. New shell and narrative text is an original adaptation, not an imported crew conversation. The parent repository license applies to original project code; the upstream TempleOS font retains its documented public-domain provenance.
