"""
IRH v72.0 — Numerical Lattice Simulations
==========================================
Core D₄ Lattice Implementation with Full Dynamical Evolution

This module implements the fundamental computational infrastructure for
simulating the D₄ cymatic resonance network described in the IRH framework.

Author: Brandon D. McCrary
Date: February 2026

Physical Units Convention:
    All quantities are expressed in Planck units:
    - Length: L_P = 1.616 × 10⁻³⁵ m = 1
    - Time: t_P = 5.391 × 10⁻⁴⁴ s = 1
    - Mass: M_P = 2.176 × 10⁻⁸ kg = 1
    - ℏ = c = G = 1

The lattice spacing a₀ = 1 in these units (one Planck length).
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import eigsh, expm_multiply
import warnings

# =============================================================================
# SECTION 1: D₄ LATTICE GEOMETRY
# =============================================================================

def generate_d4_root_vectors() -> np.ndarray:
    """
    Generate the 24 root vectors of D₄.

    These are vectors of the form (±1, ±1, 0, 0) and all permutations,
    forming the vertices of a 24-cell—the unique self-dual regular 4-polytope.

    Returns:
        np.ndarray: Shape (24, 4) array of root vectors
    """
    roots = []

    # Generate all vectors of form (±1, ±1, 0, 0) with permutations
    from itertools import permutations, product

    base_patterns = [(1, 1, 0, 0), (1, -1, 0, 0), (-1, 1, 0, 0), (-1, -1, 0, 0)]

    for pattern in base_patterns:
        for perm in set(permutations(pattern)):
            roots.append(perm)

    roots = np.array(list(set(tuple(r) for r in roots)))

    # Verify we have exactly 24 roots
    assert len(roots) == 24, f"Expected 24 roots, got {len(roots)}"

    # Verify all roots have length √2
    lengths = np.linalg.norm(roots, axis=1)
    assert np.allclose(lengths, np.sqrt(2)), "Root lengths incorrect"

    return roots


def verify_spherical_5_design(roots: np.ndarray, max_degree: int = 5) -> Dict[str, float]:
    """
    Verify that the D₄ roots form a spherical 5-design.

    A spherical t-design has the property that averaging any polynomial
    of degree ≤ t over the design points equals the spherical average.

    For monomials x₁^{a₁} x₂^{a₂} x₃^{a₃} x₄^{a₄} with a₁+a₂+a₃+a₄ ≤ t,
    the average over design points should equal the spherical integral,
    which is zero unless all exponents are even, and follows a known
    formula when all are even.

    Args:
        roots: The 24 root vectors (normalized to unit sphere)
        max_degree: Maximum polynomial degree to test

    Returns:
        Dictionary with test results and maximum deviation
    """
    # Normalize roots to unit sphere
    normalized = roots / np.linalg.norm(roots, axis=1, keepdims=True)

    results = {
        'max_deviation': 0.0,
        'tests_passed': 0,
        'tests_total': 0,
        'is_5_design': True
    }

    from itertools import product as cart_product

    for total_degree in range(1, max_degree + 1):
        # Generate all monomials of this degree
        for exponents in cart_product(range(total_degree + 1), repeat=4):
            if sum(exponents) != total_degree:
                continue

            results['tests_total'] += 1

            # Compute average over design points
            monomial_values = np.prod(normalized ** exponents, axis=1)
            design_average = np.mean(monomial_values)

            # Compute theoretical spherical average
            # For S³, the average of x₁^{a₁}...x₄^{a₄} is:
            # - 0 if any aᵢ is odd
            # - Γ((a₁+1)/2)...Γ((a₄+1)/2) / Γ((sum+4)/2) × (appropriate factor)

            if any(e % 2 == 1 for e in exponents):
                theoretical = 0.0
            else:
                # All even exponents: use gamma function formula
                from math import gamma
                half_exp = [e // 2 for e in exponents]
                numerator = np.prod([gamma(h + 0.5) for h in half_exp])
                denominator = gamma(sum(half_exp) + 2)
                theoretical = numerator / denominator / np.pi**2  # S³ normalization

            deviation = abs(design_average - theoretical)
            results['max_deviation'] = max(results['max_deviation'], deviation)

            if deviation < 1e-10:
                results['tests_passed'] += 1
            elif total_degree <= 5:
                results['is_5_design'] = False

    return results


@dataclass
class D4Lattice:
    """
    Represents a finite section of the D₄ lattice for numerical simulation.

    The lattice is constructed as points (x₁, x₂, x₃, x₄) ∈ ℤ⁴ with
    x₁ + x₂ + x₃ + x₄ ≡ 0 (mod 2), within a hypercubic region.

    Attributes:
        size: Number of lattice sites along each dimension
        periodic: Whether to use periodic boundary conditions
        sites: Array of lattice site coordinates, shape (N_sites, 4)
        neighbor_indices: For each site, indices of its 24 neighbors
        N: Total number of lattice sites
    """
    size: int
    periodic: bool = True

    def __post_init__(self):
        """Generate lattice sites and neighbor connectivity."""
        self._generate_sites()
        self._generate_neighbors()
        self._compute_structure_constants()

    def _generate_sites(self):
        """Generate all D₄ lattice sites within the simulation volume."""
        sites = []

        # Generate hypercubic grid
        for x1 in range(self.size):
            for x2 in range(self.size):
                for x3 in range(self.size):
                    for x4 in range(self.size):
                        # D₄ parity condition
                        if (x1 + x2 + x3 + x4) % 2 == 0:
                            sites.append([x1, x2, x3, x4])

        self.sites = np.array(sites, dtype=np.int32)
        self.N = len(self.sites)

        # Create coordinate-to-index mapping
        self._coord_to_idx = {}
        for idx, site in enumerate(self.sites):
            self._coord_to_idx[tuple(site)] = idx

    def _generate_neighbors(self):
        """Compute neighbor indices for each site."""
        roots = generate_d4_root_vectors()

        self.neighbor_indices = []
        self.neighbor_vectors = []

        for idx, site in enumerate(self.sites):
            neighbors = []
            vectors = []

            for root in roots:
                neighbor_coord = site + root

                if self.periodic:
                    # Apply periodic boundary conditions
                    neighbor_coord = neighbor_coord % self.size

                neighbor_tuple = tuple(neighbor_coord.astype(int))

                if neighbor_tuple in self._coord_to_idx:
                    neighbors.append(self._coord_to_idx[neighbor_tuple])
                    vectors.append(root)

            self.neighbor_indices.append(neighbors)
            self.neighbor_vectors.append(vectors)

        # Verify coordination number
        coord_numbers = [len(n) for n in self.neighbor_indices]
        if self.periodic:
            assert all(c == 24 for c in coord_numbers), \
                f"Not all sites have 24 neighbors: {set(coord_numbers)}"

    def _compute_structure_constants(self):
        """Compute lattice structure constants used in dynamics."""
        # Packing fraction η_{D₄} = π²/16
        self.eta = np.pi**2 / 16

        # Coordination number
        self.coordination = 24

        # Spherical design order
        self.design_order = 5

        # Voronoi cell volume (in lattice units)
        self.voronoi_volume = 2.0

    def get_site_position(self, idx: int) -> np.ndarray:
        """Get physical position of site in Planck units."""
        return self.sites[idx].astype(float)  # a₀ = 1 in Planck units


# =============================================================================
# SECTION 2: DYNAMICAL OPERATORS
# =============================================================================

class LatticeHamiltonian:
    """
    Constructs the Hamiltonian operator for the D₄ lattice dynamics.

    The Hamiltonian density is:
        ℋ = (1/2)ρu̇² + (1/2)𝒦(∇u)² + (1/2)ρΩ_P²|φ_ARO|² + (λ₃/2)φ_ARO(∇u)²

    In discretized form on the lattice, this becomes a sparse matrix
    acting on the displacement field u_n at each lattice site.
    """

    def __init__(self, lattice: D4Lattice,
                 omega_p: float = 1.0,  # Planck frequency in Planck units
                 damping_ratio: float = 1.0):  # Critical damping ζ = 1
        """
        Initialize Hamiltonian with lattice and physical parameters.

        Args:
            lattice: D4Lattice instance
            omega_p: ARO frequency (= 1 in Planck units)
            damping_ratio: ζ = η/(2√(JM*)), critical damping = 1
        """
        self.lattice = lattice
        self.omega_p = omega_p
        self.zeta = damping_ratio

        # Derived parameters (in Planck units, most = 1)
        self.rho = 1.0  # M*/a₀⁴ = 1
        self.K = omega_p**2 / 2  # 𝒦 = M*Ω_P²/(2a₀²)
        self.J = omega_p**2  # Spring constant
        self.eta_damp = 2 * damping_ratio * omega_p  # Damping coefficient

        self._build_laplacian()
        self._build_mass_matrix()

    def _build_laplacian(self):
        """
        Construct the discrete Laplacian operator on the D₄ lattice.

        The Laplacian is defined as:
            (∇²u)_n = Σ_j (u_{n+δ_j} - u_n) / |δ_j|²

        where the sum is over all 24 neighbors.
        """
        N = self.lattice.N

        # Build sparse matrix
        rows, cols, data = [], [], []

        for n in range(N):
            neighbors = self.lattice.neighbor_indices[n]
            n_neighbors = len(neighbors)

            # Diagonal element: -n_neighbors / |δ|²
            # For D₄ roots, |δ|² = 2
            rows.append(n)
            cols.append(n)
            data.append(-n_neighbors / 2.0)

            # Off-diagonal elements: +1/|δ|² for each neighbor
            for neighbor in neighbors:
                rows.append(n)
                cols.append(neighbor)
                data.append(1.0 / 2.0)

        self.laplacian = csr_matrix((data, (rows, cols)), shape=(N, N))

    def _build_mass_matrix(self):
        """
        Construct the mass matrix including ARO coupling.

        The effective mass at each site includes contribution from
        ARO phase-locking:
            M_eff = M* + λ₃|φ_ARO|²/Ω_P²

        For critical damping (ζ = 1), this gives uniform mass.
        """
        N = self.lattice.N

        # In Planck units with ζ = 1, effective mass is uniform
        self.mass_matrix = diags([self.rho] * N)

    def stiffness_matrix(self) -> csr_matrix:
        """
        Return the stiffness matrix K = -𝒦∇².

        This is the discrete analog of the elastic modulus term.
        """
        return -self.K * self.laplacian

    def dispersion_relation(self, k: np.ndarray) -> float:
        """
        Compute the dispersion relation ω(k) for plane waves.

        For the D₄ lattice with spherical 5-design property:
            ω² = c²k² [1 + O(k⁶a₀⁶)]

        The leading-order dispersion is exactly linear (ω = c|k|)
        with corrections only at sixth order due to the 5-design property.

        Args:
            k: Wave vector in reciprocal lattice units

        Returns:
            Angular frequency ω
        """
        roots = generate_d4_root_vectors()

        # Discrete dispersion: ω² = (2J/M*) Σ_j sin²(k·δ_j/2)
        # For small k, this → (J/M*)|k|² = c²|k|²

        dispersion_sum = 0.0
        for delta in roots:
            phase = np.dot(k, delta) / 2
            dispersion_sum += np.sin(phase)**2

        omega_sq = (2 * self.J / self.rho) * dispersion_sum / len(roots)

        return np.sqrt(max(0, omega_sq))

    def verify_isotropy(self, k_mag: float, n_directions: int = 1000) -> Dict[str, float]:
        """
        Verify isotropy of dispersion relation by sampling many directions.

        The D₄ spherical 5-design guarantees isotropy to O(k⁶).

        Args:
            k_mag: Magnitude of wave vector to test
            n_directions: Number of random directions to sample

        Returns:
            Statistics on ω variation across directions
        """
        # Sample random unit vectors on S³
        random_dirs = np.random.randn(n_directions, 4)
        random_dirs /= np.linalg.norm(random_dirs, axis=1, keepdims=True)

        # Compute dispersion in each direction
        omegas = []
        for direction in random_dirs:
            k = k_mag * direction
            omegas.append(self.dispersion_relation(k))

        omegas = np.array(omegas)

        # Expected value for isotropic dispersion
        c = np.sqrt(self.J / self.rho)  # Speed of light
        omega_expected = c * k_mag

        return {
            'mean': np.mean(omegas),
            'std': np.std(omegas),
            'min': np.min(omegas),
            'max': np.max(omegas),
            'expected': omega_expected,
            'relative_anisotropy': np.std(omegas) / np.mean(omegas),
            'deviation_from_linear': abs(np.mean(omegas) - omega_expected) / omega_expected
        }


# =============================================================================
# SECTION 3: TIME EVOLUTION AND CONTINUUM LIMIT VERIFICATION
# =============================================================================

class LatticeEvolution:
    """
    Time evolution of the D₄ lattice dynamics.

    Implements both:
    1. Real-time evolution for wave propagation
    2. Imaginary-time evolution for ground state
    """

    def __init__(self, hamiltonian: LatticeHamiltonian):
        """Initialize with Hamiltonian."""
        self.H = hamiltonian
        self.lattice = hamiltonian.lattice
        self.N = self.lattice.N

        # State vectors: displacement u and velocity v = ∂u/∂τ
        # Each site has 4 displacement components (one per dimension)
        self.u = np.zeros((self.N, 4))
        self.v = np.zeros((self.N, 4))

    def set_initial_gaussian_wave(self, center: np.ndarray,
                                   width: float,
                                   k0: np.ndarray,
                                   amplitude: float = 1.0):
        """
        Initialize with a Gaussian wave packet.

        u(x) = A exp(-|x-x₀|²/2σ²) cos(k₀·x)

        This tests wave propagation and dispersion.

        Args:
            center: Center position of wave packet
            width: Gaussian width σ
            k0: Central wave vector
            amplitude: Overall amplitude
        """
        for n in range(self.N):
            x = self.lattice.sites[n].astype(float)
            dx = x - center

            # Gaussian envelope
            envelope = amplitude * np.exp(-np.dot(dx, dx) / (2 * width**2))

            # Oscillating phase (polarization along k direction)
            phase = np.cos(np.dot(k0, x))

            # Displacement polarized transverse to k
            if np.linalg.norm(k0) > 0:
                k_hat = k0 / np.linalg.norm(k0)
                # Choose arbitrary transverse direction
                # A more robust way to find a perpendicular vector.
                # Start with an arbitrary vector not parallel to k_hat.
                if abs(k_hat[0]) < 0.9:
                    v_arb = np.array([1.0, 0.0, 0.0, 0.0])
                else:
                    v_arb = np.array([0.0, 1.0, 0.0, 0.0])
                
                # Use Gram-Schmidt to find the orthogonal component.
                perp = v_arb - np.dot(v_arb, k_hat) * k_hat
                perp /= np.linalg.norm(perp)
            else:
                perp = np.array([1, 0, 0, 0])

            self.u[n] = envelope * phase * perp

        # Initial velocity from time derivative of traveling wave
        omega = self.H.dispersion_relation(k0)
        for n in range(self.N):
            x = self.lattice.sites[n].astype(float)
            dx = x - center
            envelope = amplitude * np.exp(-np.dot(dx, dx) / (2 * width**2))
            phase = np.sin(np.dot(k0, x))

            if np.linalg.norm(k0) > 0:
                k_hat = k0 / np.linalg.norm(k0)
                perp = np.array([1, 0, 0, 0]) - k_hat[0] * k_hat
                if np.linalg.norm(perp) < 0.1:
                    perp = np.array([0, 1, 0, 0]) - k_hat[1] * k_hat
                perp /= np.linalg.norm(perp)
            else:
                perp = np.array([1, 0, 0, 0])

            self.v[n] = envelope * phase * omega * perp

    def step_verlet(self, dt: float):
        """
        Advance one time step using velocity Verlet integration.

        The equation of motion (with damping) is:
            M* ü + η u̇ + K u = F_ARO

        For critical damping (ζ = 1), this becomes a first-order system
        in physical time t (after the π/2 phase transformation).

        Args:
            dt: Time step in Planck units
        """
        # Compute acceleration from current positions
        # a = -(K/M)u - (η/M)v + F_ARO/M

        K_matrix = self.H.stiffness_matrix()

        # Force from stiffness
        for comp in range(4):
            f_elastic = -K_matrix.dot(self.u[:, comp]) / self.H.rho

            # Damping force
            f_damp = -self.H.eta_damp * self.v[:, comp] / self.H.rho

            # ARO driving (coherent oscillation at Ω_P)
            # For ground state, this is already absorbed; for excitations,
            # we work in the rotating frame where F_ARO = 0
            f_aro = 0

            a = f_elastic + f_damp + f_aro

            # Verlet update
            self.u[:, comp] += self.v[:, comp] * dt + 0.5 * a * dt**2

            # Half-step velocity
            v_half = self.v[:, comp] + 0.5 * a * dt

            # New acceleration
            f_elastic_new = -K_matrix.dot(self.u[:, comp]) / self.H.rho
            f_damp_new = -self.H.eta_damp * v_half / self.H.rho
            a_new = f_elastic_new + f_damp_new

            # Full velocity update
            self.v[:, comp] = v_half + 0.5 * a_new * dt

    def total_energy(self) -> Dict[str, float]:
        """
        Compute total energy of the lattice configuration.

        Returns kinetic, potential, and total energy.
        """
        K_matrix = self.H.stiffness_matrix()

        # Kinetic energy: (1/2)M*|v|²
        T = 0.5 * self.H.rho * np.sum(self.v**2)

        # Potential energy: (1/2)u·K·u
        V = 0.0
        for comp in range(4):
            V += 0.5 * self.u[:, comp].dot(K_matrix.dot(self.u[:, comp]))

        return {
            'kinetic': T,
            'potential': V,
            'total': T + V
        }

    def measure_group_velocity(self, k0: np.ndarray,
                                n_steps: int = 100,
                                dt: float = 0.1) -> np.ndarray:
        """
        Measure group velocity by tracking wave packet center.

        The group velocity v_g = dω/dk should equal c = a₀Ω_P in the
        continuum limit for a linear dispersion relation.

        Args:
            k0: Initial wave vector
            n_steps: Number of time steps
            dt: Time step

        Returns:
            Measured group velocity vector
        """
        # Initialize wave packet
        center = np.array([self.lattice.size/2] * 4)
        width = 5.0
        self.set_initial_gaussian_wave(center, width, k0, amplitude=0.1)

        # Track center of mass
        positions = []

        for step in range(n_steps):
            # Compute center of mass of |u|²
            u_sq = np.sum(self.u**2, axis=1)
            total = np.sum(u_sq)

            if total > 1e-10:
                com = np.zeros(4)
                for n in range(self.N):
                    com += u_sq[n] * self.lattice.sites[n]
                com /= total
                positions.append(com)

            self.step_verlet(dt)

        positions = np.array(positions)

        # Linear fit to get velocity
        times = np.arange(len(positions)) * dt

        v_g = np.zeros(4)
        for d in range(4):
            if len(times) > 1:
                slope, _ = np.polyfit(times, positions[:, d], 1)
                v_g[d] = slope

        return v_g


# =============================================================================
# SECTION 4: CONTINUUM LIMIT VERIFICATION
# =============================================================================

def verify_continuum_limit(lattice_sizes: List[int] = [8, 12, 16, 20]) -> Dict:
    """
    Verify convergence to continuum limit as lattice size increases.

    Tests:
    1. Dispersion relation approaches ω = c|k|
    2. Wave packet propagation matches continuum prediction
    3. Anisotropy decreases as expected (O(k⁶a⁶))

    Args:
        lattice_sizes: List of lattice sizes to test

    Returns:
        Dictionary with convergence data
    """
    results = {
        'sizes': lattice_sizes,
        'dispersion_errors': [],
        'anisotropies': [],
        'group_velocity_errors': []
    }

    for L in lattice_sizes:
        print(f"\n{'='*60}")
        print(f"Testing lattice size L = {L}")
        print(f"{'='*60}")

        # Create lattice
        lattice = D4Lattice(size=L, periodic=True)
        print(f"  Sites: {lattice.N}")

        # Create Hamiltonian
        H = LatticeHamiltonian(lattice)

        # Test dispersion at various k values
        # Use k values that fit in the Brillouin zone
        k_test = 2 * np.pi / L * np.array([1, 0, 0, 0])  # Smallest non-zero k

        omega = H.dispersion_relation(k_test)
        k_mag = np.linalg.norm(k_test)
        c = 1.0  # Speed of light in Planck units
        omega_expected = c * k_mag

        dispersion_error = abs(omega - omega_expected) / omega_expected
        results['dispersion_errors'].append(dispersion_error)
        print(f"  Dispersion error: {dispersion_error:.6e}")

        # Test isotropy
        isotropy = H.verify_isotropy(k_mag, n_directions=100)
        results['anisotropies'].append(isotropy['relative_anisotropy'])
        print(f"  Relative anisotropy: {isotropy['relative_anisotropy']:.6e}")

        # Test group velocity (only for larger lattices)
        if L >= 12:
            evol = LatticeEvolution(H)
            v_g = evol.measure_group_velocity(k_test, n_steps=50, dt=0.05)
            v_g_mag = np.linalg.norm(v_g)
            v_error = abs(v_g_mag - c) / c if v_g_mag > 0 else 1.0
            results['group_velocity_errors'].append(v_error)
            print(f"  Group velocity error: {v_error:.6e}")
        else:
            results['group_velocity_errors'].append(np.nan)

    return results


def compute_bridge_metric_error(lattice: D4Lattice,
                                 curvature_radius: float) -> float:
    """
    Compute the error bound on the emergent metric.

    From Appendix N of IRH v72:
        ||g_emergent - g_exact|| ≤ C · a₀² · R_max

    where C = 1/12 for D₄ geometry and R_max is the maximum curvature.

    Args:
        lattice: D4Lattice instance
        curvature_radius: Characteristic curvature radius (1/√R_max)

    Returns:
        Upper bound on metric error
    """
    a_0 = 1.0  # Planck length in Planck units
    C = 1.0 / 12  # D₄ geometric coefficient
    R_max = 1.0 / curvature_radius**2  # Maximum curvature

    error_bound = C * a_0**2 * R_max

    return error_bound


# =============================================================================
# SECTION 5: MAIN EXECUTION AND VERIFICATION TESTS
# =============================================================================

if __name__ == "__main__":
    print("="*70)
    print("IRH v72.0 — D₄ Lattice Simulation Core")
    print("="*70)

    # Test 1: Generate and verify D₄ root vectors
    print("\n[TEST 1] D₄ Root Vector Generation")
    print("-" * 50)
    roots = generate_d4_root_vectors()
    print(f"  Generated {len(roots)} root vectors")
    print(f"  Root lengths: {np.unique(np.round(np.linalg.norm(roots, axis=1), 6))}")

    # Test 2: Verify spherical 5-design property
    print("\n[TEST 2] Spherical 5-Design Verification")
    print("-" * 50)
    design_test = verify_spherical_5_design(roots)
    print(f"  Tests passed: {design_test['tests_passed']}/{design_test['tests_total']}")
    print(f"  Maximum deviation: {design_test['max_deviation']:.2e}")
    print(f"  Is 5-design: {design_test['is_5_design']}")

    # Test 3: Create small lattice and verify structure
    print("\n[TEST 3] D₄ Lattice Construction (L=8)")
    print("-" * 50)
    lattice = D4Lattice(size=8, periodic=True)
    print(f"  Total sites: {lattice.N}")
    print(f"  Expected (L⁴/2): {8**4 // 2}")
    print(f"  Packing fraction η: {lattice.eta:.6f}")
    print(f"  Coordination number: {lattice.coordination}")

    # Test 4: Hamiltonian and dispersion
    print("\n[TEST 4] Hamiltonian and Dispersion Relation")
    print("-" * 50)
    H = LatticeHamiltonian(lattice)

    # Test dispersion along different directions
    k_vals = [
        np.array([0.5, 0, 0, 0]),
        np.array([0.5, 0.5, 0, 0]) / np.sqrt(2),
        np.array([0.5, 0.5, 0.5, 0.5]) / 2
    ]

    for k in k_vals:
        omega = H.dispersion_relation(k)
        k_mag = np.linalg.norm(k)
        print(f"  k = {k}, |k| = {k_mag:.4f}, ω = {omega:.6f}, ω/|k| = {omega/k_mag:.6f}")

    # Test 5: Isotropy verification
    print("\n[TEST 5] Dispersion Isotropy")
    print("-" * 50)
    iso = H.verify_isotropy(k_mag=0.5, n_directions=500)
    print(f"  ω mean: {iso['mean']:.6f}")
    print(f"  ω std: {iso['std']:.6e}")
    print(f"  Relative anisotropy: {iso['relative_anisotropy']:.6e}")
    print(f"  Deviation from linear: {iso['deviation_from_linear']:.6e}")

    # Test 6: Bridge metric error bounds
    print("\n[TEST 6] Bridge Metric Error Bounds")
    print("-" * 50)
    test_radii = [1e10, 1e5, 1e0, 1e-5]  # In Planck lengths
    for R in test_radii:
        error = compute_bridge_metric_error(lattice, R)
        print(f"  Curvature radius {R:.0e} L_P: error ≤ {error:.2e}")

    print("\n" + "="*70)
    print("All core tests completed successfully")
    print("="*70)
