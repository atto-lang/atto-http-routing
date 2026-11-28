# PR #9 forward-port

Historical head f4f0d0d6bb1bfb80803c484579de4a85317a1d69; current base 5d9b2a72997e334c0aec518ef2cf243694d0d177.

Retain current main's generation identity and structural decision checks rather than overwrite them with the older .ores source. Forward-port all ten historical edge-case fixture/golden pairs to canonical .atto extensions, flattened into the existing guest runner glob, with implicit readonly borrowing and string value equality. 141 assertion call sites. Existing tests and source are retained. Historical host scripts and adapter-document changes still require comparison for unique behavior; no executed guest or merge-readiness claim yet.
