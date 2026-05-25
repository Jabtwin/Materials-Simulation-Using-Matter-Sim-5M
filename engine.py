import os
import sys
import io
import contextlib
import numpy as np
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"

from ase import Atoms, units
from ase.cell import Cell
from ase.build import bulk
from ase.md.langevin import Langevin
from ase.md.npt import NPT
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
from ase.thermochemistry import IdealGasThermo
from ase.vibrations import Vibrations
from ase.eos import EquationOfState
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from mattersim.forcefield import MatterSimCalculator
from mattersim.applications.phonon import PhononWorkflow
from mattersim.applications.relax import Relaxer

def prepare_structure(atoms, is_molecule=False):
    """
    Prepare structure for calculation. 
    If molecule, place in a vacuum box and center it.
    """
    if is_molecule:
        atoms.center(vacuum=10.0)
        atoms.set_pbc([True, True, True])
    return atoms

def run_equilibrium_scan(atoms, pct_range, npts):
    """
    Perform an equilibrium scan (Energy vs Lattice constant).
    Returns arrays of lattice constants and corresponding energies.
    """
    a0 = atoms.get_cell_lengths_and_angles()[0]
    scale_factors = np.linspace(1 - pct_range, 1 + pct_range, npts)
    a_vals = a0 * scale_factors
    energies = np.zeros_like(a_vals)
    cell0 = atoms.get_cell().copy()
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)

    for i, s in enumerate(scale_factors):
        atoms.set_cell(cell0 * s, scale_atoms=True)  # Scale uniformly
        energies[i] = atoms.get_potential_energy()

    # Restore original cell
    atoms.set_cell(cell0, scale_atoms=True)
    return a_vals, energies

def run_equation_of_state(atoms, pct_range=0.04, npts=15):
    """
    Compute Equation of State to find Bulk Modulus with optimized sampling range and shape relaxation.
    """
    try:
        from ase.filters import ExpCellFilter
    except ImportError:
        from ase.constraints import ExpCellFilter
    from ase.optimize import LBFGS
    from ase.eos import EquationOfState
    from ase import units
    import numpy as np
    
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    
    # 1. Important step: Optimize the entire structure (both a and c for HCP) at P=0 before scanning
    # This ensures the c/a ratio is most accurate and the E-V curve will be absolutely smooth.
    opt = LBFGS(ExpCellFilter(atoms), logfile=None)
    opt.run(fmax=0.01, steps=50)
        
    a0 = atoms.get_cell_lengths_and_angles()[0]
    scale_factors = np.linspace(1 - pct_range, 1 + pct_range, npts)
    energies = np.zeros(npts)
    volumes = np.zeros(npts)
    cell0 = atoms.get_cell().copy()

    # 2. Isotropic volume scanning (Isotropic Scaling)
    for i, s in enumerate(scale_factors):
        atoms.set_cell(cell0 * s, scale_atoms=True)
        # SKIP RELAXATION INSIDE THE LOOP TO AVOID NOISE FOR FITTING FUNCTION
        energies[i] = atoms.get_potential_energy()
        volumes[i] = atoms.get_volume()

    atoms.set_cell(cell0, scale_atoms=True)  # restore

    # 3. Fit with Birch-Murnaghan, with safe fallback if data is slightly skewed
    try:
        eos = EquationOfState(volumes, energies, eos='birchmurnaghan')
        v0, e0, B = eos.fit()
    except RuntimeError:
        # Fallback to simple Parabola equation if Birch-Murnaghan fails
        eos = EquationOfState(volumes, energies, eos='parabola')
        v0, e0, B = eos.fit()
        
    B_GPa = B / units.GPa

    return volumes, energies, eos, v0, B_GPa

def run_relaxation(atoms, verbose=False, is_molecule=False):
    """
    Relax atomic positions and cell (unless is_molecule=True).
    """
    from ase.optimize import BFGS
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    
    with contextlib.redirect_stdout(sys.stdout if verbose else io.StringIO()):
        if is_molecule:
            # For molecules, use BFGS directly on atoms to ONLY relax positions.
            dyn = BFGS(atoms, logfile=None)
            converged = dyn.run(fmax=0.01, steps=500)
            relaxed_atoms = atoms
        else:
            # For bulk, use MatterSim's Relaxer which handles cell filtering.
            relaxer = Relaxer()
            converged, relaxed_atoms = relaxer.relax(atoms, fmax=0.01, steps=500, verbose=verbose)
            
        results = {
            'steps': 500 if not converged else "converged",
            'energy': relaxed_atoms.get_potential_energy(),
            'fmax': np.max(np.linalg.norm(relaxed_atoms.get_forces(), axis=1)),
            'final_atoms': relaxed_atoms
        }
    return results

def run_tensile_test(atoms, strain_max=0.15, steps=15, is_molecule=False, orientation='[001]', phase='bcc'):
    """
    Diagnostic Version of Tensile Test: Prints internal data for crystallography troubleshooting.
    """
    from ase.filters import ExpCellFilter
    from ase.optimize import BFGS
    from ase.build import surface, bulk as bulk_ase
    
    print(f"\n{'='*60}")
    print(f"  DIAGNOSTIC TENSILE TEST: {orientation} Direction")
    print(f"{'='*60}")
    
    # 0. Calculator Setup
    if atoms.calc is None:
        atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    original_calc = atoms.calc
    
    # 1. Orientation Handling (Transformation Matrix)
    if not is_molecule and orientation == '[111]':
        from ase.build import make_supercell
        n_atoms = len(atoms)
        vol = atoms.get_volume()
        
        # Estimate a_param
        if n_atoms == 0 or vol <= 1e-6:
            a_param = 2.87 
        else:
            factor = 4.0 if phase.lower() == 'fcc' else 2.0
            a_param = (vol / n_atoms * factor)**(1/3)
            
        symbol = atoms.get_chemical_symbols()[0]
        
        # Create original bulk
        if phase.lower() == 'hcp':
            # HCP cannot be made cubic, we make it Orthorhombic
            temp_bulk = bulk_ase(symbol, crystalstructure='hcp', a=a_param, orthorhombic=True)
        else:
            temp_bulk = bulk_ase(symbol, crystalstructure=phase.lower() if phase.lower() != 'compound' else 'bcc', a=a_param, cubic=True)
        
        # Define transformation matrix P to bring the diagonal direction to the Z axis
        # Note: P for HCP may be different, but we use similar logic to create anisotropy
        if phase.lower() == 'fcc':
            P = [[-1, 1, 0], [-1, -1, 2], [1, 1, 1]]
        elif phase.lower() == 'hcp':
            # P matrix for HCP to create stable orthogonal Supercell
            P = [[1, 0, 0], [0, 1, 0], [0, 0, 1]] # Keep orthorhombic HCP if [111] is chosen
        else:
            P = [[1, -1, 0], [1, 1, -2], [1, 1, 1]]
            
        atoms = make_supercell(temp_bulk, P)
        
        # IMPORTANT STEP: Rotate so [111] direction aligns with Z-axis
        # Helps eliminate Shear Stress and correctly measure Young's Modulus in [111] direction
        atoms.rotate(atoms.cell[2], [0, 0, 1], rotate_cell=True)
        atoms.pbc = True 
        print(f"[*] [111] Cell aligned with global Z-axis.")
        
    # 2. Supercell Selection
    if not is_molecule:
        if orientation == '[111]':
            atoms = atoms * (1, 1, 3) # ~36 atoms
        else:
            atoms = atoms * (2, 2, 4) # ~32 atoms
        atoms.calc = original_calc
        print(f"[*] Total Atoms: {len(atoms)}")
        print(f"[*] Initial Cell Matrix:\n{atoms.get_cell()}")
    
    # 3. Initial Relaxation
    print("\n[*] Step 0: Initial Relaxation (Zero-stress state)")
    if not is_molecule:
        # Lock shears during initial relaxation to keep cell orthogonal
        ecf_init = ExpCellFilter(atoms, mask=[True, True, True, False, False, False])
        opt_init = BFGS(ecf_init, logfile=None)
        opt_init.run(fmax=0.01, steps=100)
    
    cell0 = atoms.get_cell().copy()
    l0_x, l0_y, l0_z = cell0[0, 0], cell0[1, 1], cell0[2, 2]
    e0 = atoms.get_potential_energy()
    
    strains = np.linspace(0, strain_max, steps)
    stresses = []
    poisson_ratios = []
    
    print(f"\n{'Step':>4} | {'Strain':>8} | {'Stress Tensor (Voigt - GPa)':>45} | {'dE (eV)':>8}")
    print("-" * 80)
    
    for i, strain in enumerate(strains):
        if atoms.calc is None: atoms.calc = original_calc
        
        # Apply strain
        new_cell = atoms.get_cell().copy()
        new_cell[2, 2] = l0_z * (1.0 + strain)
        atoms.set_cell(new_cell, scale_atoms=True)
        
        # Relax (Poisson only, lock shear)
        if not is_molecule:
            ecf = ExpCellFilter(atoms, mask=[True, True, False, False, False, False])
            opt = BFGS(ecf, logfile=None)
            opt.run(fmax=0.01, steps=100)
        
        # Diagnostics
        stress_voigt = -atoms.get_stress(voigt=True) / units.GPa
        energy = atoms.get_potential_energy()
        de = energy - e0
        e0 = energy
        
        # Get fractional coords of first 2 atoms
        frac_coords = atoms.get_scaled_positions()[:2]
        
        stress_z = stress_voigt[2]
        stresses.append(stress_z)
        
        # Poisson Calculation
        nu = 0.0
        if strain > 0.005: 
            curr_cell = atoms.get_cell()
            strain_x = (curr_cell[0, 0] - l0_x) / l0_x
            strain_y = (curr_cell[1, 1] - l0_y) / l0_y
            nu = -(strain_x + strain_y) / (2.0 * strain)
            poisson_ratios.append(nu)
            
        # Print Diagnostics row
        stress_str = "[" + ", ".join([f"{s:6.2f}" for s in stress_voigt]) + "]"
        print(f"{i:>4} | {strain*100:7.2f}% | {stress_str} | {de:8.4f}")
        # Print fractional coords to see Z movement
        print(f"       Atom 0 frac: {frac_coords[0][2]:.4f} | Atom 1 frac: {frac_coords[1][2]:.4f}")
        
    stresses = np.array(stresses)
    stresses = stresses - stresses[0]
    
    if len(stresses) > 1 and stresses[1] < 0:
        stresses = -stresses
        
    avg_nu = np.mean(poisson_ratios) if poisson_ratios else 0.3
    
    print("-" * 80)
    print(f"[*] Diagnostic Run Finished. Avg Poisson: {avg_nu:.4f}")
    print(f"{'='*60}\n")
        
    return strains, stresses, avg_nu

def run_phonon(atoms, work_dir, is_molecule=False):
    """
    Physically accurate Phonon calculation with Data Journey Tracking.
    """
    import os, io, contextlib, sys
    from phonopy import Phonopy
    from phonopy.structure.atoms import PhonopyAtoms
    
    os.makedirs(work_dir, exist_ok=True)
    plot_path = os.path.join(work_dir, "phonon_plot.png")
    
    print(f"\n--- START PHONON TASK (Molecule={is_molecule}) ---")
    
    # STEP 1: Check input structure
    print(f"STEP 1: Check input structure...")
    print(f"DEBUG: Received {len(atoms)} atoms. Formula: {atoms.get_chemical_formula()}")
    
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    forces = atoms.get_forces()
    max_f = np.max(np.abs(forces))
    print(f"DEBUG: Current Max Force: {max_f:.6f} eV/Ã…")
    if max_f > 0.05:
         print("âš ï¸ WARNING: Force is still large (>0.05), Phonon results may be imaginary or flat! Please Relax first.")

    # 1. Setup Structure & Supercell
    if is_molecule:
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)
        sc_matrix = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    else:
        sc_matrix = [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
    
    ph_atoms = PhonopyAtoms(symbols=atoms.get_chemical_symbols(),
                            scaled_positions=atoms.get_scaled_positions(),
                            cell=atoms.get_cell())
    
    phon = Phonopy(ph_atoms, supercell_matrix=sc_matrix)
    phon.generate_displacements(distance=0.03)
    supercells = phon.supercells_with_displacements
    
    # STEP 2: Calculate force constants
    print(f"STEP 2: Calculating forces with MatterSim (Total {len(supercells)} structures)...")
    original_symbols = atoms.get_chemical_symbols()
    forces_list = []
    for i, sc in enumerate(supercells):
        if sc is None: continue
        num_sc = len(sc.positions) // len(atoms)
        sc_symbols = original_symbols * num_sc
        ase_sc = Atoms(symbols=sc_symbols, positions=sc.positions, cell=sc.cell, pbc=True)
        ase_sc.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
        forces_list.append(ase_sc.get_forces())
        if i % 5 == 0: print(f"DEBUG: Processing {i}/{len(supercells)}...")
        
    phon.forces = np.array(forces_list)
    phon.produce_force_constants()
    print("DEBUG: Successfully created force constant matrix.")

    # STEP 3: Special handling for molecule/crystal
    print(f"STEP 3: Process vibrational spectra (Discrete/Bands)...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    has_imag = False
    
    try:
        if is_molecule:
            # --- MOLECULE DOS: Use Histogram to avoid _smearing_function error ---
            molecule_freqs = phon.get_frequencies([0, 0, 0])
            phys_modes = molecule_freqs[molecule_freqs > 0.1]
            ax1.hist(phys_modes, bins=30, color='red', alpha=0.7, rwidth=0.8)
            ax1.set_title("Molecular Vibration DOS")
            ax1.set_xlabel("Frequency (THz)")
            
            # --- MOLECULE LEVELS: Draw horizontal lines ---
            for f in phys_modes:
                ax2.axhline(y=f, color='red', linewidth=1.5, alpha=0.8)
            ax2.set_xlim(-0.5, 0.5)
            ax2.set_xticks([0])
            ax2.set_xticklabels(['Gamma'])
            ax2.set_title("Molecular Energy Levels")
        else:
            # --- CRYSTAL DOS ---
            print("STEP 3: Extracting DOS data for crystal...")
            # Use finer Mesh [20, 20, 20] for professional reports
            phon.run_mesh([20, 20, 20])
            phon.run_total_dos()
            
            # Get standard frequencies from mesh_dict (Instead of get_frequencies_all which fails)
            mesh_dict = phon.get_mesh_dict()
            all_freqs = mesh_dict['frequencies']
            max_f = np.max(all_freqs)
            print(f"DEBUG: Highest frequency found: {max_f:.2f} THz")

            if max_f < 0.01:
                print("âš ï¸ WARNING: Frequency is still approximately 0. Please check the Relaxation step!")

            # Get data manually to plot (Avoid API 'ax' incompatibility error)
            dos_dict = phon.get_total_dos_dict()
            ax1.plot(dos_dict['frequency_points'], dos_dict['total_dos'], color='blue', linewidth=1.5)
            ax1.fill_between(dos_dict['frequency_points'], dos_dict['total_dos'], color='blue', alpha=0.3)
            ax1.set_title(f"Phonon DOS (Max: {max_f:.1f} THz)")
            ax1.set_xlabel("Frequency (THz)")
            ax1.set_ylabel("Density of States (states/THz)")
            
            # --- CRYSTAL BANDS ---
            q_points = [[0, 0, 0], [0.5, 0.5, -0.5], [0, 0.5, 0], [0, 0, 0]]
            path_conns = [np.linspace(q_points[i], q_points[i+1], 51) for i in range(len(q_points)-1)]
            phon.run_band_structure(path_conns)
            band_dict = phon.get_band_structure_dict()
            for d, f in zip(band_dict['distances'], band_dict['frequencies']):
                ax2.plot(d, f, color='red', linewidth=1.5)
            ax2.set_xlim(band_dict['distances'][0][0], band_dict['distances'][-1][-1])
            
            # Add High-Symmetry Points for X-axis
            q_ticks = [
                band_dict['distances'][0][0],
                band_dict['distances'][0][-1],
                band_dict['distances'][1][-1],
                band_dict['distances'][2][-1]
            ]
            q_labels = [r'$\Gamma$', 'L', 'X', r'$\Gamma$']
            ax2.set_xticks(q_ticks)
            ax2.set_xticklabels(q_labels)
            
            # Draw vertical lines separating Brillouin Zone at symmetry points
            for tick in q_ticks[1:-1]:
                ax2.axvline(x=tick, color='gray', linestyle='--', linewidth=0.8, alpha=0.7)
                
            ax2.set_title("Phonon Dispersion (Bands)")
            ax2.set_xlabel("Wave Vector")
            
        ax2.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax2.set_ylabel("Frequency (THz)")
        ax2.grid(True, alpha=0.3)
        ax1.grid(True, alpha=0.3)
        
        # Check has_imag
        phon.run_mesh([10, 10, 10])
        all_freqs = phon.get_mesh_dict()['frequencies']
        has_imag = np.any(all_freqs < -0.1)
        
    except Exception as e:
        print(f"ERROR at STEP 3: {e}")
        ax2.text(0.5, 0.5, f"Error: {e}", ha='center', transform=ax2.transAxes)

    # STEP 4: Save and report
    print(f"STEP 4: Plotting and saving file...")
    plt.tight_layout()
    fig.savefig(plot_path)
    plt.close(fig)
    print(f"DEBUG: Saved image at {plot_path}")
    print(f"--- COMPLETED PHONON TASK --- \n")
    
    return has_imag, fig, plot_path

    return has_imag, fig, plot_path

def run_molecular_dynamics(atoms, T, steps, num_gpus, ensemble='NVT', pressure_GPa=0.0):
    """
    Run Molecular Dynamics using Langevin (NVT) or NPT ensemble.
    """
    from ase.md.langevin import Langevin
    from ase.constraints import FixCom
    from ase import units
    
    use_gpu = num_gpus > 0
    device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    
    # Raise threshold to 128 atoms to stabilize temperature (Delta T ~ 1/sqrt(N))
    if len(atoms) < 128:
        multiplier = int(np.ceil((128 / len(atoms))**(1/3)))
        atoms = atoms * (multiplier, multiplier, multiplier)
        atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)

    # Add Relaxation step to remove excess internal energy (Structural shock) before providing kinetic energy
    from ase.optimize import LBFGS
    opt = LBFGS(atoms, logfile=None)
    opt.run(fmax=0.05, steps=20)

    # Fix center of mass using Constraint instead of fixcm in Langevin
    atoms.set_constraint(FixCom())

    # Initialize velocities
    MaxwellBoltzmannDistribution(atoms, temperature_K=T)
    
    if ensemble.upper() == 'NPT':
        from ase.md.npt import NPT
        dyn = NPT(atoms, timestep=1 * units.fs, temperature_K=T, 
                  externalstress=pressure_GPa * units.GPa,
                  ttime=25 * units.fs, 
                  pfactor=75 * units.GPa * (100 * units.fs)**2,
                  logfile=None)
    else:
        # Use fixcm=False per new ASE standard, increase friction to 0.01 for faster temperature recovery
        dyn = Langevin(atoms, timestep=1 * units.fs, temperature_K=T, friction=0.01, fixcm=False, logfile=None)
    
    energies = []
    temps = []
    volumes = []
    
    interval = max(1, steps // 50)  # log 50 points regardless of step count
    
    def log_step():
        energies.append(atoms.get_total_energy())
        t = atoms.get_temperature()
        temps.append(t if t is not None else 0.0)
        volumes.append(atoms.get_volume())
        
    dyn.attach(log_step, interval=interval)
    
    n_runs = max(1, steps // interval)
    
    import time
    print(f"\n{'='*60}")
    print(f"  STARTING MOLECULAR DYNAMICS ({ensemble})")
    print(f"  Target Temp: {T} K | Total Steps: {steps}")
    print(f"{'='*60}")
    
    start_time = time.time()
    for i in range(n_runs):
        dyn.run(interval)
        
        progress = (i + 1) / n_runs * 100
        elapsed = time.time() - start_time
        eta = elapsed / (i + 1) * (n_runs - i - 1)
        curr_t = temps[-1] if temps else 0.0
        
        print(f"[{progress:>5.1f}%] Step {(i+1)*interval:>5}/{steps} | Temp: {curr_t:>6.1f} K | ETA: {eta:>5.1f}s", end='\r', flush=True)
        
    print(f"\n{'='*60}")
    print(f"[*] MD Run Finished in {time.time() - start_time:.1f}s")
    print(f"{'='*60}\n")
        
    times = np.arange(len(energies)) * interval * 1.0  # times in fs
    return times, np.array(energies), np.array(temps), np.array(volumes)

def run_diffusion(atoms, T=300, steps=1000, num_gpus=0):
    """
    Expert Diffusion Analysis: Vacancy-mediated MD with accurate unit conversion.
    """
    import numpy as np
    from ase.md.langevin import Langevin
    from ase import units
    from ase.md.velocitydistribution import MaxwellBoltzmannDistribution
    from ase.constraints import FixCom
    
    print(f"\n{'='*55}")
    print(f"  EXPERT DIFFUSION ANALYSIS: T={T} K")
    print(f"{'='*55}")
    
    use_gpu = num_gpus > 0
    device = "cuda" if (use_gpu and torch.cuda.is_available()) else "cpu"
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    
    # 1. Create large Supercell (at least 128 atoms) for stable Temp
    if len(atoms) < 128:
        multiplier = int(np.ceil((128 / len(atoms))**(1/3)))
        atoms = atoms * (multiplier, multiplier, multiplier)
        atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    
    # 2. CREATE VACANCY - Key to diffusion in solid phase
    if len(atoms) > 1:
        del atoms[0]
        print(f"[*] Vacancy created. Running with {len(atoms)} atoms.")

    # 3. Fix center of mass and Initialize velocities at T_target
    atoms.set_constraint(FixCom())
    MaxwellBoltzmannDistribution(atoms, temperature_K=T)
    
    timestep_fs = 1.0
    dyn = Langevin(atoms, timestep=timestep_fs * units.fs, temperature_K=T, friction=0.01, fixcm=False, logfile=None)
    
    # 4. Thermal equilibration (Equilibration)
    equil_steps = max(100, int(steps * 0.1))
    print(f"[*] Phase 1: Equilibration ({equil_steps} steps)...")
    dyn.run(equil_steps)
    
    # 5. Data collection (Production)
    print(f"[*] Phase 2: Production ({steps} steps)...")
    pos0 = atoms.get_positions().copy()
    msds = []
    times_ps = []
    
    print(f"{'-'*50}")
    print(f"{'Step':>8} | {'Time (ps)':>10} | {'Temp (K)':>10} | {'MSD (A^2)':>10}")
    print(f"{'-'*50}")
    
    log_interval = max(1, steps // 15)
    for s in range(0, steps, log_interval):
        dyn.run(log_interval)
        curr_pos = atoms.get_positions()
        diff = curr_pos - pos0
        msd = np.mean(np.sum(diff**2, axis=1))
        
        current_step = (s + log_interval)
        current_time_ps = current_step * timestep_fs / 1000.0
        
        msds.append(msd)
        times_ps.append(current_time_ps)
        
        print(f"{current_step:>8} | {current_time_ps:>10.4f} | {atoms.get_temperature():>10.2f} | {msd:>10.4f}")
        
    times_ps = np.array(times_ps)
    msds = np.array(msds)
    
    # 6. Calculate coefficient D (Einstein Relation: MSD = 6Dt)
    if len(times_ps) > 1:
        # Fit Production region (skip point 0 if needed, here polyfit handles it)
        slope, intercept = np.polyfit(times_ps, msds, 1)
        # D_A2_ps = slope / 6.0 (A^2/ps)
        # Convert to cm^2/s: 1 A^2/ps = 1e-4 cm^2/s
        D_cm2_s = (slope / 6.0) * 1e-4
    else:
        D_cm2_s = 0.0
        
    print(f"{'-'*50}")
    print(f"[*] Diffusion Coefficient D: {D_cm2_s:.4e} cm^2/s")
    print(f"{'='*55}\n")
    
    return times_ps, msds, D_cm2_s

def get_gibbs_energy(symbol, phase, T_range, P_GPa, calc=None):
    """
    Calculate Gibbs Free Energy G(T, P) = E_pot + PV + F_vib
    """
    from ase.build import bulk
    try:
        from ase.filters import ExpCellFilter
    except ImportError:
        from ase.constraints import ExpCellFilter
    from ase.optimize import LBFGS
    from ase import units
    import numpy as np
    
    # 1. Initialize structure
    a_dict = {"bcc": 2.87, "fcc": 3.64, "hcp": 2.45}
    a_param = a_dict.get(phase.lower(), 2.87)
    
    try:
        atoms = bulk(symbol, phase.lower(), a=a_param, cubic=True)
    except:
        atoms = bulk(symbol, phase.lower(), a=a_param)
    
    # Use provided calculator
    atoms.calc = calc if calc else MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    
    if P_GPa > 0:
        ecf = ExpCellFilter(atoms, scalar_pressure=P_GPa * units.GPa)
        opt = LBFGS(ecf, logfile=None)
        opt.run(fmax=0.05, steps=50)
    
    E_pot = atoms.get_potential_energy()
    Vol = atoms.get_volume()
    # PV work in eV
    PV_work = P_GPa * Vol * 0.0062415 
    
    # 2. Get F_vib (Vibrational part ONLY)
    try:
        T_list, F_vib_list, _, _ = run_thermodynamics(atoms, is_crystal=True, include_E0=False, calc=atoms.calc)
    except TypeError:
        T_list, F_vib_list, _, _ = run_thermodynamics(atoms, is_crystal=True)
        
    # FIX: Flatten array to avoid 'object too deep' error
    T_arr = np.array(T_list, dtype=float).flatten()
    F_vib_arr = np.array(F_vib_list, dtype=float).flatten()
    
    # Re-sort to ensure consistency for np.interp
    sort_idx = np.argsort(T_arr)
    F_vib_interp = np.interp(T_range, T_arr[sort_idx], F_vib_arr[sort_idx])
    
    # G = E_pot + PV + F_vib (NORMALIZED PER ATOM)
    G_total = E_pot + PV_work + F_vib_interp
    n_atoms = len(atoms)
    return G_total / n_atoms

def run_phase_diagram(element, phase1, phase2, Tmin, Tmax, Pmin, Pmax):
    """
    Expert Phase Diagram: Finding transition temperatures with unified calculator.
    """
    import numpy as np
    import sys
    import logging
    
    # --- TURN OFF MATTERSIM SPAM LOG ---
    try:
        from loguru import logger
        logger.remove() 
        logger.add(sys.stderr, level="WARNING") 
    except: pass
    logging.getLogger("mattersim").setLevel(logging.WARNING)
    
    print(f"\n[SYSTEM] Initializing MatterSim AI Brain for {element}...")
    unified_calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    print(f"[SYSTEM] Brain loaded. Starting phase analysis.\n")
    
    print(f"{'='*60}")
    print(f"  PHASE BOUNDARY ANALYSIS: {phase1} vs {phase2}")
    print(f"{'='*60}")
    
    # Zoom into pressure range 0 - 6 GPa to capture curve with high resolution (30 points)
    P_points = np.linspace(0, 6.0, 30)
    
    Tmin_safe = max(50.0, float(Tmin))
    T_sweep = np.linspace(Tmin_safe, float(Tmax), 200)
    
    boundary_T = []
    boundary_P = []
    
    for i, p in enumerate(P_points):
        progress = (i + 1) / len(P_points) * 100
        print(f"[{progress:>5.1f}%] Analyzing Pressure: {p:>6.2f} GPa | Comparing {phase1} vs {phase2}...", end='\r', flush=True)
        
        try:
            g1 = get_gibbs_energy(element, phase1, T_sweep, p, calc=unified_calc)
            g2 = get_gibbs_energy(element, phase2, T_sweep, p, calc=unified_calc)
            
            # Find sign change point of Gibbs difference
            diff = g1 - g2
            idx = np.where(np.diff(np.sign(diff)))[0]
            if len(idx) > 0:
                i_idx = idx[0]
                # Linear interpolation to find absolute exact T at diff == 0
                t1, t2 = T_sweep[i_idx], T_sweep[i_idx+1]
                d1, d2 = diff[i_idx], diff[i_idx+1]
                
                # Formula to find x-axis intersection
                t_trans = t1 - d1 * (t2 - t1) / (d2 - d1)
                
                boundary_T.append(t_trans)
                boundary_P.append(p)
        except Exception as e:
            print(f"\n    [!] Error at {p:.2f} GPa: {e}")
            
    print(f"\n{'='*60}")
    print(f"[*] Analysis Complete. Found {len(boundary_T)} boundary points.")
    print(f"{'='*60}\n")
            
    return np.array(boundary_T), np.array(boundary_P)

def run_thermodynamics(atoms, is_crystal=True, include_E0=True, calc=None):
    """
    Calculate thermodynamic properties (G, S, Cv) vs Temperature.
    """
    T_arr = np.linspace(10, 1000, 100) 
    kB = units.kB
    
    # Use provided calculator or assign new if none
    if calc:
        atoms.calc = calc
    elif atoms.calc is None:
        atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
        
    E0 = atoms.get_potential_energy()
    N = len(atoms)

    if is_crystal:
        # --- Debye Model for Crystals ---
        # Calculate Bulk Modulus for Debye Temp estimate
        strains = [0.98, 1.0, 1.02]
        configs = []
        for s in strains:
            at = atoms.copy()
            at.set_cell(atoms.get_cell() * s, scale_atoms=True)
            # REUSE LOADED BRAIN, DO NOT REINITIALIZE
            at.calc = atoms.calc 
            configs.append(at)
        
        vols = [a.get_volume() for a in configs]
        energies = [a.get_potential_energy() for a in configs]
        
        poly = np.polyfit(vols, energies, 2)
        v0 = -poly[1] / (2 * poly[0])
        B = v0 * 2 * poly[0] # eV/A^3
        B_GPa = B * 160.21766 
        
        avg_mass = np.mean(atoms.get_masses())
        theta_D = 200 * np.sqrt(max(10, B_GPa) / avg_mass)
        
        omega_D = kB * theta_D 
        n_modes = 3 * N
        phonon_energies = np.linspace(0, omega_D, 101)[1:]
        phonon_DOS = phonon_energies**2
        phonon_DOS = phonon_DOS / phonon_DOS.sum()

        G, S, Cv = [], [], []
        for T_val in T_arr:
            kT = kB * T_val
            x = phonon_energies / kT
            x = np.clip(x, 1e-10, 500) # Clip x to prevent exp overflow
            
            ZPE = 0.5 * np.dot(phonon_DOS, phonon_energies) * n_modes
            # RESTORE STANDARD FORMULA OF F_VIB TO RETURN SCALAR
            F_vib = ZPE + kT * np.sum(phonon_DOS * n_modes * np.log(1 - np.exp(-x) + 1e-300))
            
            # G = E0 + F_vib if requested, else only take F_vib
            G_val = (E0 + F_vib) if include_E0 else F_vib
            G.append(G_val)
            
            n_occ = 1.0 / (np.exp(x) - 1.0 + 1e-300)
            Svib = kB * n_modes * np.sum(phonon_DOS * ((x * (n_occ + 1)) - x - np.log(1 - np.exp(-x) + 1e-300)))
            cv_val = kB * n_modes * np.sum(phonon_DOS * (x**2 * np.exp(x) / (np.exp(x) - 1 + 1e-150)**2))
            
            S.append(Svib)
            Cv.append(cv_val)

    else:
        # --- Ideal Gas Model for Molecules ---
        # PBC must be False for moments of inertia calculation
        orig_pbc = atoms.get_pbc()
        atoms.set_pbc(False)
        
        try:
            # CACHE FIX: Set specific name and clean up junk files to avoid reading old force matrix
            vib_name = f'vib_{atoms.get_chemical_formula()}'
            vib = Vibrations(atoms, name=vib_name)
            vib.clean() # Delete old file if any
            
            vib.run()
            # Vibrational energies (exclude translations and rotations)
            freqs = vib.get_frequencies()
            
            # Detect geometry
            moments = atoms.get_moments_of_inertia()
            if len(atoms) == 1:
                geom = 'monatomic'
            elif (moments > 1e-3).sum() == 2:
                geom = 'linear'
            else:
                geom = 'nonlinear'
                
            thermo = IdealGasThermo(
                vib_energies=vib.get_energies(),
                potentialenergy=E0,
                atoms=atoms,
                geometry=geom,
                symmetrynumber=1,
                spin=0
            )
            pressure = 101325 # 1 atm
            G = [thermo.get_gibbs_energy(temp, pressure=pressure) for temp in T_arr]
            S = [thermo.get_entropy(temp, pressure=pressure) for temp in T_arr]
            
            # Calculate Cv by numerical derivative of Internal Energy (U)
            Cv_list = []
            dT_step = 0.1 # Small temperature step to calculate derivative
            for temp in T_arr:
                # Avoid negative or too small temperature when stepping back
                t_safe = max(temp, dT_step + 1e-5)
                U_plus = thermo.get_internal_energy(t_safe + dT_step, verbose=False)
                U_minus = thermo.get_internal_energy(t_safe - dT_step, verbose=False)
                # Central derivative: Cv = dU / dT
                cv_val = (U_plus - U_minus) / (2 * dT_step)
                Cv_list.append(cv_val)
            Cv = np.array(Cv_list)
            
            # Clean up junk files immediately after calculating
            vib.clean()
        finally:
            atoms.set_pbc(orig_pbc)

    return (T_arr, np.array(G), np.array(S), np.array(Cv))


def run_vapor_pressure(atoms, Tmin, Tmax):
    """
    Calculate vapor pressure P(T) using Clausius-Clapeyron equation.
    Delta H_vap is approximated by the cohesive energy.
    """
    # 1. Calculate Bulk Energy per atom
    atoms.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    E_bulk = atoms.get_potential_energy() / len(atoms)
    
    # 2. Calculate Isolated Atom Energy
    from ase import Atoms as ASEAtoms
    symbol = atoms.get_chemical_symbols()[0]
    single_atom = ASEAtoms(symbols=[symbol], positions=[(0, 0, 0)])
    single_atom.set_cell([20, 20, 20]) # Large vacuum box
    single_atom.set_pbc(True)
    single_atom.calc = MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    E_atom = single_atom.get_potential_energy()
    
    # 3. Cohesive Energy (Heat of Vaporization)
    H_vap = E_atom - E_bulk # in eV
    
    # 4. Temperature range
    T_arr = np.linspace(Tmin, Tmax, 100)
    
    # 5. Clausius-Clapeyron: P = P0 * exp(-H_vap / (kB * T))
    kB = units.kB # eV/K
    P0 = 1e5      # Reference pressure in Pa
    
    # Avoid division by zero if T=0
    T_safe = np.where(T_arr == 0, 1e-10, T_arr)
    P_arr = P0 * np.exp(-H_vap / (kB * T_safe))
    
    return T_arr, P_arr, H_vap

def run_defect_analysis(atoms, defect_type, supercell_size=3, dopant_element=None, calc=None):
    """
    Calculate Defect Formation Energy.
    """
    import copy
    import time
    import numpy as np
    from ase import Atom, Atoms
    from ase.optimize import LBFGS
    try:
        from ase.filters import ExpCellFilter
    except ImportError:
        from ase.constraints import ExpCellFilter

    # --- 1. PREPARE SUPERCELL ---
    if isinstance(supercell_size, int):
        sc_matrix = (supercell_size, supercell_size, supercell_size)
    else:
        sc_matrix = supercell_size
        
    print(f"\n{'='*60}")
    print(f"  DEFECT ANALYSIS: {defect_type.upper()}")
    print(f"{'='*60}")
    
    if len(atoms) < 20:
        perfect_sc = atoms * sc_matrix
    else:
        perfect_sc = atoms.copy()
        print("Note: Input structure seems large enough, not applying supercell scaling.")
    
    perfect_sc.calc = calc if calc else MatterSimCalculator(load_path="MatterSim-v1.0.0-5M.pth", device=device)
    unified_calc = perfect_sc.calc 

    # --- 2. RELAX PERFECT STRUCTURE ---
    print(f"[*] Step 1: Relaxing Perfect Supercell ({len(perfect_sc)} atoms)...")
    t0 = time.time()
    
    ecf_perf = ExpCellFilter(perfect_sc)
    opt_perf = LBFGS(ecf_perf, logfile=None)
    opt_perf.run(fmax=0.01, steps=100)
    
    E_perfect = perfect_sc.get_potential_energy()
    N_host_perfect = len(perfect_sc)
    mu_host = E_perfect / N_host_perfect
    print(f"    -> E_perfect = {E_perfect:.4f} eV")
    print(f"    -> Host Chemical Potential (mu_host) = {mu_host:.4f} eV/atom")
    print(f"    -> Time: {time.time()-t0:.1f}s")
    
    # --- 3. CREATE DEFECT ---
    print(f"\n[*] Step 2: Creating {defect_type} defect...")
    defective_sc = perfect_sc.copy()
    defective_sc.calc = unified_calc
    
    target_idx = len(defective_sc) // 2 
    
    dn_host = 0
    dn_dopant = 0
    mu_dopant = 0.0
    
    if defect_type.lower() == "vacancy":
        del defective_sc[target_idx]
        dn_host = -1
        print(f"    -> Removed host atom at index {target_idx}.")
        
    elif defect_type.lower() == "substitutional":
        if not dopant_element:
            raise ValueError("Dopant element must be provided for Substitutional defect.")
        defective_sc[target_idx].symbol = dopant_element
        dn_host = -1
        dn_dopant = 1
        print(f"    -> Replaced host atom at index {target_idx} with {dopant_element}.")
        
    elif defect_type.lower() == "interstitial":
        if not dopant_element:
            raise ValueError("Dopant element must be provided for Interstitial defect.")
        
        cell_center = np.sum(defective_sc.get_cell(), axis=0) / 2.0
        offset = np.array([0.5, 0.5, 0.5]) 
        interstitial_pos = cell_center + offset
        
        defective_sc.append(Atom(dopant_element, position=interstitial_pos))
        dn_dopant = 1
        print(f"    -> Inserted {dopant_element} at interstitial site {interstitial_pos}.")
    else:
        raise ValueError(f"Unknown defect type: {defect_type}")

    # Calculate mu_dopant if needed
    if dn_dopant > 0:
        print(f"\n[*] Step 3: Calculating Dopant Chemical Potential (mu_{dopant_element})...")
        single_dopant = Atoms(symbols=[dopant_element], positions=[(0,0,0)])
        single_dopant.set_cell([15, 15, 15]) 
        single_dopant.set_pbc(True)
        single_dopant.calc = unified_calc
        mu_dopant = single_dopant.get_potential_energy()
        print(f"    -> mu_{dopant_element} (Isolated Atom) = {mu_dopant:.4f} eV/atom")

    # --- 4. RELAX DEFECTIVE STRUCTURE ---
    print(f"\n[*] Step 4: Relaxing Defective Supercell ({len(defective_sc)} atoms)...")
    t1 = time.time()
    
    opt_defect = LBFGS(defective_sc, logfile=None)
    opt_defect.run(fmax=0.01, steps=150)
    
    E_defect = defective_sc.get_potential_energy()
    print(f"    -> E_defect = {E_defect:.4f} eV")
    print(f"    -> Time: {time.time()-t1:.1f}s")
    
    # --- 5. CALCULATE FORMATION ENERGY ---
    print(f"\n[*] Step 5: Calculating Formation Energy...")
    sum_mu = (dn_host * mu_host) + (dn_dopant * mu_dopant)
    E_f = E_defect - E_perfect - sum_mu
    
    print(f"{'-'*60}")
    print(f"  Defect Formation Energy (E_f): {E_f:.4f} eV")
    print(f"{'-'*60}\n")
    
    return E_f, E_perfect, E_defect, mu_host, mu_dopant, perfect_sc, defective_sc

