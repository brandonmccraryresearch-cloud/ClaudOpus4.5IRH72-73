# IRH v73.1 — Section I.3 (Corrected)

## Lattice Selection: The Viability Criterion

Having established that the fundamental substrate must be a discrete lattice rather than a continuum, we now face the question of *which* lattice. The space of possible 4-dimensional lattices is, of course, infinite—but physical constraints dramatically narrow the field.

It seems reasonable to propose that a viable lattice must satisfy at least four criteria, each arising from distinct physical requirements:

### Criterion 1: Packing Efficiency (η)

The sphere packing density measures how efficiently the lattice fills space. A loosely-packed lattice would leave "holes" in the vacuum structure, which one might expect to manifest as pathological singularities or instabilities. We therefore seek lattices with high packing fractions.

### Criterion 2: Coordination Number (κ)

The kissing number—the count of nearest neighbors—determines the connectivity of the lattice and hence the richness of possible interactions. Too few neighbors yields a sparse, disconnected structure; too many may introduce unwanted redundancies.

### Criterion 3: Triality (T)

As we shall argue in Chapter III, the three generations of Standard Model fermions appear to arise from the triality automorphism of SO(8). This remarkable property exists *only* for SO(8)—it has no analog in SO(n) for n ≠ 8. The D₄ lattice is the unique 4-dimensional lattice whose symmetry group contains SO(8) with its triality structure.

### Criterion 4: Isotropy (S)

A spherical t-design is a finite set of points on the sphere such that the average of any polynomial of degree ≤ t over those points equals the average over the full sphere. The D₄ root system constitutes a spherical 5-design, ensuring that lattice physics is isotropic up to fifth-order corrections. This appears necessary for Lorentz invariance to emerge in the continuum limit.

---

## The Viability Index

We combine these criteria into a single figure of merit:

$$V = \eta \times \kappa \times T \times S$$

where T = 1 if the lattice admits triality and 0 otherwise. The comparison among 4D lattice candidates is instructive:

| Lattice | η (Packing) | κ (Kissing) | T (Triality) | S (Design) | V |
|:--------|:------------|:------------|:-------------|:-----------|--:|
| D₄      | π²/16 ≈ 0.617 | 24 | 1 | 5 | **74.0** |
| Z⁴      | π²/32 ≈ 0.308 | 8  | 0 | 3 | 0 |
| A₄      | √5/8 ≈ 0.280  | 10 | 0 | 2 | 0 |

The D₄ lattice dominates this comparison—indeed, it is the *only* lattice with nonzero Viability Index, owing to its unique possession of triality. The index value of 74.0 is perhaps less significant than the binary fact: D₄ passes the triality test; no other 4D lattice does.

One might worry that this criterion is circular—we have, after all, defined the index to favor triality-bearing lattices. But the circularity is only apparent. The *physical* requirement is that the theory reproduce three generations of fermions. Triality is the *mathematical* structure that accomplishes this. We did not choose triality because it selects D₄; we chose it because it explains the generational structure, and it happens that D₄ is the unique 4D lattice that provides it.

---

## A Note on the Packing Densities

The reader may verify that the D₄ packing density of π²/16 ≈ 0.617 makes it the densest known sphere packing in four dimensions. This is a nontrivial mathematical fact—the sphere packing problem remains unsolved in most dimensions, though significant progress has been made in recent years.

By contrast, the naive hypercubic lattice Z⁴ has density π²/32 ≈ 0.308—exactly half that of D₄. This geometric inefficiency, combined with its lack of triality, renders Z⁴ unsuitable for our purposes.

**Explicit verification:**

For D₄:
- Minimal vector length: √2 (e.g., the vector (1, 1, 0, 0))
- Sphere radius for packing: √2/2
- Fundamental domain volume: 2 (in standard normalization)
- Sphere volume in 4D: V₄(r) = (π²/2)r⁴ = (π²/2)(√2/2)⁴ = π²/8
- Packing density: η = (π²/8)/2 = **π²/16 ≈ 0.617**

For Z⁴:
- Minimal vector length: 1 (e.g., the vector (1, 0, 0, 0))
- Sphere radius for packing: 1/2
- Unit cell volume: 1
- Sphere volume: V₄(1/2) = (π²/2)(1/2)⁴ = π²/32
- Packing density: η = **π²/32 ≈ 0.308**

---

## Historical Remark

It is worth noting that the D₄ lattice has appeared in physics before, though not (to my knowledge) in this fundamental role. It arises naturally in the context of SO(8) gauge theory, in certain string compactifications, and in the theory of quaternionic structures. Whether these appearances reflect deeper connections or mere mathematical coincidence remains, at this stage, unclear.

---

## Erratum

*An earlier version of this manuscript (v72.0) contained two errors in the Viability Index table:*

1. *The Z⁴ packing density was incorrectly listed as 0.617 (identical to D₄). The correct value is π²/32 ≈ 0.308.*

2. *The D₄ Viability Index was stated as 44.4. The correct value is 0.617 × 24 × 1 × 5 = **74.0**.*

*These were arithmetic/transcription errors that do not affect the theoretical conclusions, since the selection mechanism depends only on whether V > 0 (i.e., whether triality exists), not on the numerical value of V. The errors have been corrected in this version.*

---

*The preceding analysis suggests that D₄ is not merely a convenient choice, but arguably the unique lattice compatible with the observed structure of particle physics. The remainder of this work explores the consequences of this identification.*

---

**Brandon D. McCrary**
*February 2026 — Version 73.1*
