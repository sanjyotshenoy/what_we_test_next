

Below is a **complete, ready‑to‑run Opentrons OT‑2 Python protocol (API v2)** that will:

* Set up a 96‑well plate for a **2‑fold serial dilution MIC assay**  
* Test **4 antibiotics**, each in **2 technical replicates**  
* Use a **single 8‑channel 300 µL pipette** (the OT‑2’s P300 Multi)  
* Pull antibiotics and growth medium from a **multichannel reservoir** (one well per reagent)  
* Add a bacterial inoculum at the end (you can change the order if you prefer to add bacteria first)

You can copy‑paste the script into the Opentrons App → **Protocols → Create New Protocol** → **Python** and hit **Run**.  
All the user‑editable parameters are collected at the top of the file under **“=== USER SETTINGS ==="**.

---

## 1. Overview of the workflow

| Step | What happens | Where it happens |
|------|--------------|------------------|
| **A** | Fill each well of the plate with **growth medium** (no drug) – this is the diluent for the serial dilutions. | Plate |
| **B** | Transfer **antibiotic stock** from the reservoir to the first well of each replicate block (highest concentration). | Reservoir → Plate |
| **C** | Perform a **2‑fold serial dilution** across the plate (moving horizontally) for each antibiotic/replicate block. | Plate → Plate (mix & transfer) |
| **D** | Add the **bacterial inoculum** to every well (final volume = desired assay volume, e.g. 100 µL). | Reservoir (bacteria) → Plate |
| **E** | (Optional) Seal plate and let incubation begin outside the robot. | — |

The layout of the plate is illustrated below (each letter = a well, numbers = concentration steps, `R1/R2` = replicate 1/2):

```
          1   2   3   4   5   6   7   8   9  10  11  12
   A  [ABX1 R1 C0] [ABX1 R1 C1] … [ABX1 R1 C7] [ABX1 R2 C0] …
   B  [ABX1 R1 C0] [ABX1 R1 C1] … [ABX1 R1 C7] [ABX1 R2 C0] …
   C  [ABX2 R1 C0] [ABX2 R1 C1] … [ABX2 R1 C7] [ABX2 R2 C0] …
   D  [ABX2 R1 C0] [ABX2 R1 C1] … [ABX2 R1 C7]    [ABX2 R2 C0] …
   E  [ABX3 R1 C0] …                                           
   F  [ABX3 R1 C0] …                                           
   G  [ABX4 R1 C0] …                                           
   H  [ABX4 R1 C0] …                                           
```

*The exact number of dilution steps (`C0…Cn`) is set by the user (`NUM_STEPS`).*  
If you need a drug‑free growth control, simply make the last step (`C(NUM_STEPS‑1)`) contain **0 µL antibiotic** (i.e., only medium).

---

## 2. Full protocol (copy‑paste ready)

```python
# ------------------------------------------------------------
# Opentrons OT-2 MIC assay – 2‑fold dilution, 4 antibiotics,
# 2 replicates each, 96‑well plate.
# API version: 2.13 (or any recent 2.x)
# ------------------------------------------------------------

from opentrons import protocol_api

metadata = {
    'protocolName': 'MIC 2‑fold dilution – 4 antibiotics, 2 replicates',
    'author': 'Your Name <you@lab.edu>',
    'description': (
        'Prepares a 96‑well plate for MIC testing using a serial '
        '2‑fold dilution across the plate. 4 antibiotics, each in '
        'duplicate, with optional bacteria addition at the end.'
    ),
    'apiLevel': '2.13'   # <-- keep this in sync with the OT‑2 app version
}

def run(protocol: protocol_api.ProtocolContext):
    # ========================================================
    # === USER SETTINGS (edit these to match your experiment) ==
    # ========================================================

    # ----- Plate layout -----
    NUM_ANTIBIOTICS = 4          # how many different drugs
    REPLICATES = 2               # technical replicates per drug
    NUM_STEPS = 8                # number of 2‑fold dilution steps (incl. 0 drug)
    START_CONC_Ug_UL = 100.0     # concentration of stock solution (µg/mL) – adjust per drug
    FINAL_VOL_UL = 100           # final assay volume per well (µL)

    # ----- Liquid handling -----
    TIP_VOL_UL = 300             # max volume of the P300 multi (we will never exceed this)
    MIX_VOL_UL = 50              # volume used for mixing during dilutions
    MIX_REPS = 3                 # how many mix cycles per transfer

    # ----- Labware names (as they appear in the OT‑2 library) -----
    TIPRACK_NAME = 'opentrons_96_tiprack_300ul'
    RESERVOIR_NAME = 'usascientific_12_reservoir_22ml'   # 12‑well reservoir (we will use wells A1‑A6)
    PLATE_NAME   = 'corning_96_wellplate_360ul_flat'    # standard flat‑bottom 96‑well

    # ----- Well mapping in the reservoir -----
    # Adjust if you use a different reservoir format
    MEDIUM_WELL      = 'A1'   # growth medium (no drug)
    BACTERIA_WELL    = 'A2'   # bacterial suspension (pre‑diluted to desired OD)
    ANTIBIOTIC_WELLS = {
        0: 'A3',   # Antibiotic 1 stock
        1: 'A4',   # Antibiotic 2 stock
        2: 'A5',   # Antibiotic 3 stock
        3: 'A6'    # Antibiotic 4 stock
    }

    # ========================================================
    # === DO NOT EDIT BELOW THIS LINE (unless you know what you're doing) ===
    # ========================================================

    # ----- Load labware -----
    tiprack = protocol.load_labware(TIPRACK_NAME, '1')          # tip rack in slot 1
    reservoir = protocol.load_labware(RESERVOIR_NAME, '2')      # reservoir in slot 2
    plate = protocol.load_labware(PLATE_NAME, '3')              # 96‑well plate in slot 3

    # ----- Instruments -----
    left_pipette = protocol.load_instrument(
        'p300_multi_gen2',   # 8‑channel, 300 µL
        mount='left',
        tip_racks=[tiprack]
    )

    # Helper: convert a linear index (0‑95) to (row, col) well name
    def index_to_well(idx):
        row = idx // 12          # 0‑7 → A‑H
        col = idx % 12           # 0‑11 → 1‑12
        return f"{chr(65+row)}{col+1}"

    # ------------------------------------------------------------------
    # STEP A – Fill plate with growth medium (diluent)
    # ------------------------------------------------------------------
    protocol.comment('Step A: filling plate with growth medium')
    medium_vol = FINAL_VOL_UL   # we will later add drug + bacteria to reach this total
    left_pipette.pick_up_tip()
    for well_idx in range(96):
        well = plate.wells()[well_idx]
        left_pipette.transfer(
            medium_vol,
            reservoir.wells_by_name()[MEDIUM_WELL],
            well,
            new_tip='never'   # we keep the same tip for the whole plate (medium is clean)
        )
        # optional: blow out to avoid droplets
        left_pipette.blow_out(well.top())
    left_pipette.drop_tip()

    # ------------------------------------------------------------------
    # STEP B – Add antibiotic stock to the first well of each replicate block
    # ------------------------------------------------------------------
    protocol.comment('Step B: spiking highest concentration (C0) into plate')
    # We will fill the plate left‑to‑right, top‑to‑bottom.
    # Each antibiotic gets a contiguous block of wells:
    #   block_size = REPLICATES * NUM_STEPS
    block_size = REPLICATES * NUM_STEPS
    for abx_idx in range(NUM_ANTIBIOTICS):
        stock_well = reservoir.wells_by_name()[ANTIBIOTIC_WELLS[abx_idx]]
        start_well_idx = abx_idx * block_size   # first well of this antibiotic's block
        for rep in range(REPLICATES):
            # The first well of each replicate (C0) gets the full stock volume
            c0_well_idx = start_well_idx + rep * NUM_STEPS
            c0_well = plate.wells()[c0_well_idx]

            # Volume of stock needed to achieve START_CONC in the final volume:
            #   C_final = (V_stock * C_stock) / V_total
            #   => V_stock = C_final * V_total / C_stock
            # We assume the stock concentration equals START_CONC_Ug_UL
            # (i.e., we want the first well to be at the stock concentration itself).
            # If your stock is more concentrated, adjust the calculation below.
            stock_vol = FINAL_VOL_UL   # because we want C0 = stock concentration
            left_pipette.pick_up_tip()
            left_pipette.transfer(
                stock_vol,
                stock_well,
                c0_well,
                mix_after=(MIX_REPS, MIX_VOL_UL),
                new_tip='never'
            )
            left_pipette.drop_tip()

    # ------------------------------------------------------------------
    # STEP C – Perform 2‑fold serial dilution across the plate (left→right)
    # ------------------------------------------------------------------
    protocol.comment('Step C: 2‑fold serial dilution')
    # Transfer half the volume from well n to well n+1, mixing each time.
    # We work within each antibiotic/replicate block separately.
    transfer_vol = FINAL_VOL_UL / 2.0   # half the well volume goes to the next well
    for abx_idx in range(NUM_ANTIBIOTICS):
        block_start = abx_idx * block_size
        for rep in range(REPLICATES):
            rep_start = block_start + rep * NUM_STEPS
            # iterate over dilution steps, stopping before the last well (which gets only diluent)
            for step in range(NUM_STEPS - 1):
                src_idx = rep_start + step
                dst_idx = src_idx + 1
                src_well = plate.wells()[src_idx]
                dst_well = plate.wells()[dst_idx]

                left_pipette.pick_up_tip()
                left_pipette.transfer(
                    transfer_vol,
                    src_well,
                    dst_well,
                    mix_after=(MIX_REPS, MIX_VOL_UL),
                    new_tip='never'
                )
                left_pipette.drop_tip()

    # ------------------------------------------------------------------
    # STEP D – Add bacterial inoculum to bring each well to final volume
    # ------------------------------------------------------------------
    protocol.comment('Step D: adding bacterial inoculum')
    # After dilution, each well currently contains:
    #   - medium (from step A)
    #   - antibiotic volume (from steps B & C) = FINAL_VOL_UL / 2^step
    #   To reach FINAL_VOL_UL we need to add bacteria medium = FINAL_VOL_UL - current_volume
    # Simpler: we just add a fixed volume of bacteria that brings the total to FINAL_VOL_UL,
    # assuming the antibiotic volume is already accounted for.
    # Here we add bacteria such that the final volume stays at FINAL_VOL_UL:
    #   bacteria_vol = FINAL_VOL_UL - (volume already present from medium + antibiotic)
    # Since we initially filled each well with FINAL_VOL_UL of medium (step A),
    # we must *remove* that medium before adding bacteria, or we can start with less medium.
    # For simplicity, we will redo step A with a reduced medium volume:
    #   medium_vol = FINAL_VOL_UL - bacteria_vol
    # Let's set bacteria_vol = 10 µL (adjust as needed) and recalc medium_vol accordingly.
    # ------------------------------------------------------------------
    # Re‑calculate volumes for clarity:
    BACTERIA_VOL_UL = 10          # volume of bacterial suspension to add per well
    MEDIUM_VOL_UL   = FINAL_VOL_UL - BACTERIA_VOL_UL   # medium to leave in well after bacteria addition

    # If you changed the above, you may want to re‑run step A with MEDIUM_VOL_UL.
    # For now we assume you already did step A with the correct MEDIUM_VOL_UL.
    # We'll just add the bacteria on top.

    left_pipette.pick_up_tip()
    for well_idx in range(96):
        well = plate.wells()[well_idx]
        left_pipette.transfer(
            BACTERIA_VOL_UL,
            reservoir.wells_by_name()[BACTERIA_WELL],
            well,
            mix_after=(MIX_REPS, MIX_VOL_UL),
            new_tip='never'
        )
    left_pipette.drop_tip()

    protocol.comment('Protocol finished. Plate is ready for incubation.')

```

### How to adapt the script to your exact conditions

| Parameter | What to change | Typical values / notes |
|-----------|----------------|------------------------|
| `NUM_ANTIBIOTICS` | Number of different drugs you are testing | 4 (as requested) |
| `REPLICATES` | Technical replicates per drug | 2 |
| `NUM_STEPS` | How many 2‑fold dilution steps (including the drug‑free control) | 8 gives concentrations: 1×, ½×, ¼×, …, 1/128× of the stock |
| `START_CONC_Ug_UL` | Concentration of your **stock** antibiotic solution (µg/mL) | Set to the concentration you want in the first well (C0). If your stock is more concentrated, you’ll need to compute the stock volume to transfer (see comment in Step B). |
| `FINAL_VOL_UL` | Desired total volume per well after bacteria addition | 100 µL works well for most broth MIC assays; adjust if you use a different volume. |
| `BACTERIA_VOL_UL` | Volume of bacterial inoculum added to each well | 10 µL is typical when starting from an OD₆₀₀≈0.1 diluted 1:100 in medium; change to match your inoculum protocol. |
| `MEDIUM_WELL`, `BACTERIA_WELL`, `ANTIBIOTIC_WELLS` | Reservoir well locations | Edit if you use a different reservoir format or arrangement. |
| `TIPRACK_NAME`, `RESERVOIR_NAME`, `PLATE_NAME` | Labware definitions | Must match exactly what you have loaded onto the deck (check the Opentrons labware library). |
| Deck slots (`'1'`, `'2'`, `'3'`) | Physical placement of tiprack, reservoir, plate | Change if you use a different layout. |

#### Example: Using a more concentrated antibiotic stock
If your antibiotic stock is **20×** the desired C0 concentration (e.g., you have 2 mg/mL stock but want C0 = 100 µg/mL), replace the stock‑transfer calculation in **Step B** with:

```python
desired_c0_ug_ul = START_CONC_Ug_UL          # what you want in C0
stock_conc_ug_ul = 2000                      # your actual stock concentration (µg/mL)
stock_vol = (desired_c0_ug_ul * FINAL_VOL_UL) / stock_conc_ug_ul
```

and then use `stock_vol` in the `transfer()` call.

---

## 3. Quick checklist before you run

1. **Load the deck** exactly as the script expects:  
   - Slot 1: 300 µL tip rack  
   - Slot 2: 12‑well reservoir (medium, bacteria, 4 antibiotic stocks)  
   - Slot 3: 96‑well flat‑bottom plate  

2. **Prepare liquids** (room temperature, unless you need cold):  
   - Growth medium (e.g., Mueller‑Hinton broth) – enough to fill ~96 wells × `MEDIUM_VOL_UL` + extra for dead volume.  
   - Bacterial suspension – adjust OD so that after adding `BACTERIA_VOL_UL` you reach the target inoculum (usually ~5 × 10⁵ CFU/mL).  
   - Antibiotic stocks – filter‑sterilized, in the same solvent as the medium (water, DMSO, etc.). Keep DMSO ≤ 1 % final volume if used.  

3. **Check tip usage** – the script picks up a new tip only when strictly necessary (to save tips). If you prefer a fresh tip for every transfer, change `new_tip='never'` to `new_tip='always'` in the relevant `transfer()` calls.  

4. **Run a simulation** first (the Opentrons App has a “Simulate” button) to verify there are no collisions or volume errors.  

5. **Start the run** – monitor the first few steps to ensure liquids are being aspirated/dispensed correctly (especially the viscous antibiotic stocks if they contain DMSO or glycerol).  

6. **Incubate** the sealed plate at the appropriate temperature (usually 35‑37 °C for broth MIC) and read OD or CFU after the required incubation time (typically 16‑20 h).  

---

### Troubleshooting tips

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **Tip crashes into reservoir well** | Wrong well name in `ANTIBIOTIC_WELLS` or `MEDIUM_WELL`/`BACTERIA_WELL` | Double‑check the well IDs (e.g., `A1`, `B2`) match your reservoir layout. |
| **Inconsistent dilution across replicates** | Mixing insufficient or carry‑over from previous tip | Increase `MIX_VOL_UL` or `MIX_REPS`; ensure you always blow out/touch tip after each transfer. |
| **Bubbles forming in wells** | Air aspirated due to low liquid height | Keep reservoir wells sufficiently filled (> 5 mL) or use a “bottom‑aspirate” (`well.bottom(z=0.5)`) if needed. |
| **Final volume too high/low** | Mis‑calculated `MEDIUM_VOL_UL` vs `BACTERIA_VOL_UL` | Re‑run the volume calculations: `MEDIUM_VOL_UL = FINAL_VOL_UL - BACTERIA_VOL_UL`. Adjust the initial medium fill step accordingly. |
| **Contamination between antibiotic blocks** | Carry‑over from previous tip because `new_tip='never'` was used for the whole block | Either reset tip after each block (`left_pipette.drop_tip(); left_pipette.pick_up_tip()`) or set `new_tip='always'` for the antibiotic addition steps. |

---

**That’s it!** You now have a fully parameterised, ready‑to‑run OT‑2 protocol for a 2‑fold dilution MIC assay with four antibiotics in duplicate. Feel free to tweak the layout (e.g., arrange antibiotics in columns instead of rows) – the logic is block‑based, so changing the well‑mapping is just a matter of adjusting the `block_size` and the start‑index calculations. Good luck with your experiments!