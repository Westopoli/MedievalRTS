# leaf-02 assumptions

1. **RNG byte-for-byte parity with Python is NOT possible at the leaf level.** Python `random.Random` uses Mersenne Twister; GDScript `RandomNumberGenerator` uses PCG. SPEC_GODOT.md AC-51 demands byte-for-byte match for the first 20 tile placements for seed=42 — this is impossible without reimplementing MT in GDScript, which is out of scope for this leaf. The leaf delivers GDScript-internal determinism (same seed → same terrain across calls), the statistical bounds in SPEC.md AC-30/AC-31, and the cluster-placement algorithm structure. The umbrella's byte-for-byte assertion (if it comes from the parent) will need either (a) a Python-MT port in GDScript or (b) relaxation to "structurally equivalent (counts, ranges)" — escalate to parent.

2. **`terrain` row container type:** chosen `Array` of `Array` of `String` (plain untyped Array) to match the contract's `terrain: Array = []` declaration (which doesn't constrain inner type). Each row is a plain `Array` initialized to `"grass"` strings; not `PackedStringArray`, to keep comparison and slicing semantics consistent with the rest of the sim.

3. **`Entity.pos`** is stored as `Vector2i(x, y)` (contract requires `Vector2i`). Python's `tuple[int, int]` maps to `Vector2i` per SPEC_GODOT.md AC-43.

4. **RNG ordering** mirrors Python: a single `RandomNumberGenerator` instance with `seed = <input>` is consumed in order (TC0 forest centers → TC0 forest trees → TC0 gold mines → TC1 forest centers → TC1 forest trees → TC1 gold mines). No sub-seed derivation is used at this leaf (SPEC_GODOT.md AC-51 mentions sub-seed derivation as an option but the Python source uses one RNG throughout, which we mirror).

5. **`randi_range` semantics:** GDScript `RandomNumberGenerator.randi_range(a, b)` returns an integer in `[a, b]` inclusive, matching Python's `random.Random.randint`.

6. **Boundary collision with map edges:** falls back to the Python source's behavior — silently skip out-of-bounds attempts and continue trying within the attempt budget. If a side cannot place its full 24 trees / 2 gold mines within the attempt budget, the call returns with fewer than the target — the test budget allows ±25% slack on tree count (`[20, 30]`) which accommodates this.
