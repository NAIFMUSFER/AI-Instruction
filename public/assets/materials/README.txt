Local presentation texture root (Phase 9.1).

Textures load ONLY from this directory, same-origin, and ONLY when listed in
acs_pbr.json -> texture_policy.local_texture_sets. The shipped set is EMPTY,
so the renderer performs zero texture fetches and uses the deterministic
procedural PBR materials as fallback. No CDN. No remote host. Adding a texture
here without declaring it in the specification does nothing by design.
