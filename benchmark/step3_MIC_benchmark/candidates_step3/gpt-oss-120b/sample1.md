**Minimum‑Inhibitory‑Concentration (MIC) assay on the OT‑2**  
*4 antibiotics × 2 replicates, 2‑fold serial dilution, 96‑well plate*  

---

## 1. What the protocol does

| Stage | What happens in the plate | Final volume (µL) |
|-------|---------------------------|-------------------|
| **A – Broth** | 100 µL sterile broth is added to **every well** (including the two control columns). | 100 |
| **B – Antibiotic stock** | 100 µL of a **2×‑stock** solution of each antibiotic is added to column 1.  Each antibiotic occupies two rows (its two replicates).  After mixing column 1 contains 200 µL of the highest test concentration. | 200 |
| **C – “Trim‑to‑100 µL”** | 100 µL is removed from column 1 so that every column will later hold **exactly 100 µL** of antibiotic solution (the concentration series). | 100 |
| **D – Serial 2‑fold dilution** | 100 µL is transferred from column i → column i + 1 (i = 1‑9).  After each transfer the destination is emptied back to 100 µL by discarding the extra 100 µL.  After the loop columns 1‑10 each contain 100 µL of a diluted antibiotic solution (2‑fold steps). | 100 |
| **E – Bacterial inoculum** | 100 µL of a ~5 × 10⁵ CFU mL⁻¹ suspension is added to columns 1‑11 (columns 1‑10 = test wells, column 11 = growth control).  Column 12 receives **no bacteria** (sterility control). | 200 |
| **F – Incubate & read** | Plate is sealed, incubated (usually 18‑20 h @ 35‑37 °C) and OD (or other read‑out) is taken. | – |

Because the antibiotic solution is prepared at *2×* the highest desired final concentration, the **addition of the bacterial inoculum does not change the intended concentrations** – the final well volume is 200 µL and the antibiotic concentration is exactly what the dilution series gave.

---

## 2. Plate layout (ASCII view)

```
      1   2   3   4   5   6   7   8   9  10  11  12   ← columns
   ───────────────────────────────────────────────────────
A │ A1  A2  A3  A4  A5  A6  A7  A8  A9 A10 A11 A12 │  Antibiotic‑1 (replicate 1)
B │ B1  B2  B3  B4  B5  B6  B7  B8  B9 B10 B11 B12 │  Antibiotic‑1 (replicate 2)
C │ C1  C2  C3  C4  C5  C6  C7  C8  C9 C10 C11 C12 │  Antibiotic‑2 (replicate 1)
D │ D1  D2  D3  D4  D5  D6  D7  D8  D9 D10 D11 D12 │  Antibiotic‑2 (replicate 2)
E │ E1  E2  E3  E4  E5  E6  E7  E8  E9 E10 E11 E12 │  Antibiotic‑3 (replicate 1)
F │ F1  F2  F3  F4  F5  F6  F7  F8  F9 F10 F11 F12 │  Antibiotic‑3 (replicate 2)
G │ G1  G2  G3  G4  G5  G6  G7  G8  G9 G10 G11 G12 │  Antibiotic‑4 (replicate 1)
H │ H1  H2  H3  H4  H5  H6  H7  H8  H9 H10 H11 H12 │  Antibiotic‑4 (replicate 2)
   ───────────────────────────────────────────────────────
```

*Columns 1‑10 – 2‑fold dilution series*  
*Column 11 – growth control (broth + bacteria, no drug)*  
*Column 12 – sterility control (broth only)*  

---

## 3. Reagent preparation (off‑robot)

| Reagent | Where it lives on the deck | Typical prep |
|---------|----------------------------|--------------|
| **Sterile broth** (e.g. CAMHB) | Reservoir well **A1** | Autoclave/filter‑sterilise. |
| **Bacterial suspension** (≈ 5 × 10⁵ CFU mL⁻¹) | Reservoir well **A2** | Dilute a fresh overnight culture in broth to the target density (McFarland 0.5 ≈ 1 × 10⁸ CFU mL⁻¹, then 1:200). |
| **Antibiotic 1‑4 (2×‑stocks)** | **Antibiotic stock plate** (96‑well deep‑well) – see mapping below | Dissolve each antibiotic in the appropriate solvent and dilute in broth to **2 × the highest test concentration** you want to see on the plate.  Aliquot 100 µL into the two rows that belong to that drug (see “Source‑plate map” below). |
| **Trash** | Built‑in waste container (no deck slot needed). | – |

### Source‑plate map (96‑well deep‑well plate, slot 3)

| Row | Antibiotic | Wells pre‑filled with 2×‑stock (100 µL each) |
|-----|------------|-------------------------------------------|
| A & B | Antibiotic 1 | A1, B1 |
| C & D | Antibiotic 2 | C1, D1 |
| E & F | Antibiotic 3 | E1, F1 |
| G & H | Antibiotic 4 | G1, H1 |

*(All other wells of the stock plate stay empty – they are never touched.)*  

> **Tip:** Because the OT‑2 can aspirate from a different source well with each tip, the layout above lets the **8‑channel** head add the four drugs in *one* multi‑channel transfer.

---

## 4. Deck layout (recommended)

| Slot | Labware (name used in the script) | Comments |
|------|-----------------------------------|----------|
| 1    | 300 µL tip rack – `opentrons_96_tiprack_300ul` | 8‑channel tips. |
| 2    | 96‑well assay plate – `corning_96_wellplate_360ul_flat` | The MIC plate. |
| 3    | 96‑well deep‑well stock plate – `nest_96_wellplate_2ml_deep` | Holds the four 2×‑stocks. |
| 4    | 12‑well reservoir – `usascientific_12_reservoir_22ml` | Broth (A1) + bacteria (A2). |
| (optional) | Temperature module – if you want the robot to keep the plate at 35 °C. | Not required for the liquid‑handling part. |

---

## 5. Full OT‑2 Python protocol (API 2.15)

```python
# --------------------------------------------------------------
#   OT‑2 MIC assay – 4 antibiotics, 2 replicates, 2‑fold dilution
# --------------------------------------------------------------
#   Author:  ChatGPT (2026‑11‑08)
#   API level: 2.15
# --------------------------------------------------------------

from opentrons import protocol_api

metadata = {
    'protocolName': 'MIC assay – 4 antibiotics, 2‑replicates, 2‑fold serial dilution',
    'author': 'ChatGPT',
    'description': (
        'Minimum inhibitory concentration (MIC) test on an OT‑2 using an 8‑channel '
        'P300. Four drugs, each tested in duplicate across a 10‑point 2‑fold '
        'dilution series (columns 1‑10). Column 11 = growth control, column 12 = '
        'sterility control.'
    ),
    'apiLevel': '2.15'
}


def run(protocol: protocol_api.ProtocolContext):
    ##################################################################
    # ----------------------  LABWARE & INSTRUMENTS  -----------------
    ##################################################################
    tip_rack_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    mic_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat',
        '2',
        label='MIC assay plate'
    )
    antibiotic_stock_plate = protocol.load_labware(
        'nest_96_wellplate_2ml_deep',
        '3',
        label='Antibiotic 2×‑stock plate'
    )
    reservoir = protocol.load_labware(
        'usascientific_12_reservoir_22ml',
        '4',
        label='Reagent reservoir'
    )

    # 8‑channel P300 (Gen2).  If you have a Gen1 pipette, replace with 'p300_multi'.
    p300 = protocol.load_instrument('p300_multi_gen2', mount='left',
                                    tip_racks=[tip_rack_300])

    ##################################################################
    # -----------------------  USER PARAMETERS  --------------------
    ##################################################################
    # Volumes (µL)
    BROTH_VOLUME = 100            # added to *every* well at the start
    ANTISTOCK_VOLUME = 100        # 2×‑stock added to column 1 (per replicate)
    TRANSFER_VOLUME = 100         # volume moved during each 2‑fold step
    BACTERIA_VOLUME = 100         # inoculum added later
    DISCARD_VOLUME = 100          # volume removed after each transfer (same as TRANSFER_VOLUME)

    # Columns
    N_CONC_COLS = 10               # columns 1‑10 are the dilution series
    GROWTH_CTRL_COL = 11           # column 11 (index 10) gets bacteria + broth only
    STERILITY_CTRL_COL = 12        # column 12 (index 11) stays broth only

    # ----- Reagent locations ---------------------------------------
    broth = reservoir['A1']                # sterile broth
    bacteria = reservoir['A2']             # ~5 × 10⁵ CFU mL⁻¹ suspension

    # ----- Antibiotic‑stock mapping (2 rows per drug) -------------
    #   Rows A‑B → drug 1, C‑D → drug 2, E‑F → drug 3, G‑H → drug 4.
    #   Each well in the source plate already contains the 2×‑stock.
    stock_map = {
        'A': [antibiotic_stock_plate['A1'], antibiotic_stock_plate['B1']],
        'B': [antibiotic_stock_plate['C1'], antibiotic_stock_plate['D1']],
        'C': [antibiotic_stock_plate['E1'], antibiotic_stock_plate['F1']],
        'D': [antibiotic_stock_plate['G1'], antibiotic_stock_plate['H1']],
    }

    ##################################################################
    # -----------------------  STEP 1  -----------------------------
    #  Distribute 100 µL broth to *every* well.
    ##################################################################
    protocol.comment('STEP 1 – Adding 100 µL sterile broth to all 96 wells.')
    p300.distribute(
        volume=BROTH_VOLUME,
        source=broth,
        dest=[well for well in mic_plate.wells()],
        new_tip='once',
        disposal_volume=0
    )

    ##################################################################
    # -----------------------  STEP 2  -----------------------------
    #  Add 2×‑stock antibiotic to column 1 (rows are drug‑specific).
    ##################################################################
    protocol.comment('STEP 2 – Adding 2× antibiotic stock (100 µL) to column 1.')

    # Build a list of the eight source wells that correspond to the eight tips.
    source_wells_col1 = [
        stock_map['A'][0],   # tip A → row A (drug 1)
        stock_map['A'][1],   # tip B → row B (drug 1)
        stock_map['B'][0],   # tip C → row C (drug 2)
        stock_map['B'][1],   # tip D → row D (drug 2)
        stock_map['C'][0],   # tip E → row E (drug 3)
        stock_map['C'][1],   # tip F → row F (drug 3)
        stock_map['D'][0],   # tip G → row G (drug 4)
        stock_map['D'][1]    # tip H → row H (drug 4)
    ]

    dest_wells_col1 = mic_plate.columns()[0]          # A1‑H1 (list of 8 wells)

    p300.transfer(
        volume=ANTISTOCK_VOLUME,
        source=source_wells_col1,
        dest=dest_wells_col1,
        new_tip='once',
        mix_before=(3, 50),   # gentle pre‑mix of each stock (optional)
        mix_after=(3, 50),    # ensure complete mixing in the destination well
        blow_out=True
    )

    ##################################################################
    # -----------------------  STEP 3  -----------------------------
    #  Trim column 1 back to 100 µL (remove the extra 100 µL).
    ##################################################################
    protocol.comment('STEP 3 – Removing excess volume from column 1 (100 µL waste).')
    p300.pick_up_tip()
    for well in dest_wells_col1:
        p300.aspirate(DISCARD_VOLUME, well)
        p300.dispense(DISCARD_VOLUME, protocol.trash_container.wells()[0])
    p300.drop_tip()

    ##################################################################
    # -----------------------  STEP 4  -----------------------------
    #  Serial 2‑fold dilution across columns 1‑10, discarding after each step.
    ##################################################################
    protocol.comment('STEP 4 – Performing the 2‑fold serial dilution (columns 1→10).')
    for src_idx in range(N_CONC_COLS - 1):          # 0 → 8 (col 1 to col 9 as source)
        src_col = mic_plate.columns()[src_idx]      # list of 8 source wells
        dest_col = mic_plate.columns()[src_idx + 1] # list of 8 destination wells

        # 1️⃣ Transfer 100 µL from src → dest (keeps the same 8‑tip set)
        p300.transfer(
            volume=TRANSFER_VOLUME,
            source=src_col,
            dest=dest_col,
            new_tip='never',
            mix_before=(3, 50),
            mix_after=(3, 50),
            blow_out=True
        )

        # 2️⃣ Discard the extra 100 µL from the *destination* column so that
        #    each column ends up with exactly 100 µL again.
        p300.pick_up_tip()
        for well in dest_col:
            p300.aspirate(DISCARD_VOLUME, well)
            p300.dispense(DISCARD_VOLUME, protocol.trash_container.wells()[0])
        p300.drop_tip()

    ##################################################################
    # -----------------------  STEP 5  -----------------------------
    #  Add bacterial inoculum (100 µL) to columns 1‑11.
    ##################################################################
    protocol.comment('STEP 5 – Adding bacterial suspension (100 µL) to test wells '
                     'and growth‑control column.')
    # Columns 1‑10 (index 0‑9) + growth‑control column (index 10)
    for col_idx in range(N_CONC_COLS + 1):          # 0 → 10  (col 1‑11)
        dest_col = mic_plate.columns()[col_idx]
        p300.transfer(
            volume=BACTERIA_VOLUME,
            source=bacteria,
            dest=dest_col,
            new_tip='always',
            blow_out=True
        )
    # Column 12 (sterility control) receives **no** bacteria – nothing to do.

    ##################################################################
    # -----------------------  FINISH  -----------------------------
    ##################################################################
    protocol.comment('All liquids are in place.  Seal the plate, incubate ('
                     'typically 18–20 h at 35–37 °C), then read OD600 '
                     'or your chosen endpoint.')
    # Optional pause so the user can double‑check plate orientation:
    protocol.pause('Plate is ready for sealing & incubation. '
                   'Press RESUME when you are ready to continue.')

# ----------------------------------------------------------------
# END OF PROTOCOL
# ----------------------------------------------------------------
```

### How the script works (quick walk‑through)

| Step in script | What the robot does |
|----------------|---------------------|
| **Load labware** | Tip rack, assay plate, deep‑well stock plate, 12‑well reservoir. |
| **Step 1** | `distribute` puts **100 µL broth** into *every* well – one tip‑pick is enough (`new_tip='once'`). |
| **Step 2** | `transfer` with a **list of eight source wells** (one per tip) adds **100 µL 2×‑stock** to the appropriate rows of column 1.  Each tip aspirates a *different* antibiotic. |
| **Step 3** | One tip‑pick removes the **extra 100 µL** from column 1, leaving **100 µL** behind (the “half‑volume” needed for the dilution cascade). |
| **Step 4** | A loop performs the **2‑fold serial dilution**: <br>  ① Transfer 100 µL from column i to column i + 1 (both columns already contain 100 µL broth, so after mixing the destination has double the volume). <br>  ② Immediately discard 100 µL from the destination column so it returns to 100 µL. |
| **Step 5** | `transfer` adds **100 µL bacterial inoculum** to every well of columns 1‑10 (the test dilutions) **and** column 11 (growth control). Column 12 stays bacteria‑free (sterility control). |
| **Finish** | The plate now contains **200 µL total** per test well (antibiotic + broth + bacteria).  The user can seal and incubate. |

---

## 6. Customising the protocol

| What you may want to change | Where to edit in the script | Example |
|-----------------------------|-----------------------------|---------|
| **Number of concentration points** (e.g., only 8 dilutions) | `N_CONC_COLS` (line ≈ 57). Adjust also `GROWTH_CTRL_COL` if you shift columns. | `N_CONC_COLS = 8` |
| **Total well volume** (e.g., 150 µL final) | Change `BROTH_VOLUME`, `ANTISTOCK_VOLUME`, `TRANSFER_VOLUME`, `BACTERIA_VOLUME` proportionally (see description above). | For 150 µL final: `BROTH_VOLUME = 75`, `ANTISTOCK_VOLUME = 75`, `BACTERIA_VOLUME = 75`. |
| **Use a different pipette (single‑channel) for the bacterial step** | Replace `p300.transfer(..., new_tip='always')` with a single‑channel instrument (load `p300_single`). | `p300_single = protocol.load_instrument('p300_single', 'right', tip_racks=[tip_rack_300])` then use `p300_single` in the final loop. |
| **Add a temperature module** | Load it with `temp_mod = protocol.load_module('temperature module', 5)` and place the assay plate on it (`mic_plate = temp_mod.load_labware('corning_96_wellplate_360ul_flat')`). | `temp_mod.set_temperature(35)` before the incubation step. |
| **Change the antibiotic names** | Edit the `stock_map` dictionary and (optionally) add a `drug_names = ['AMP', 'CIP', 'GEN', 'TET']` list for commenting. | `stock_map['A'] = [...]  # ampicillin` |

---

## 7. Troubleshooting & Tips

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| **Cross‑contamination between rows** (e.g., drug 1 appears in rows C‑D) | Wrong source‑well order in `source_wells_col1`. | Double‑check that the list follows the exact top‑to‑bottom order A‑H. |
| **Wells overflow after a transfer** | `TRANSFER_VOLUME` larger than the amount present, or forgetting to discard the extra 100 µL. | Verify `TRANSFER_VOLUME ≤ 100 µL` and keep the discard step (`p300.aspirate(DISCARD_VOLUME, well)`). |
| **Tip not picking up liquid** | Tips not calibrated for the 300 µL geometry, or the pipette height is too high. | Re‑calibrate the tip offset for the 300 µL tip rack (Labware → Calibrate → Tip offset). |
| **Bacterial growth in sterility control** | Contaminated broth or reservoir. | Use filter‑sterilised broth, change the reservoir, and work in a biosafety cabinet. |
| **Not enough tips** | Protocol uses more than the 96 tips available. | Add a second 300 µL tip rack (`protocol.load_labware(..., '7')`) and list it in `tip_racks=` when loading the instrument. |
| **Robot complains “cannot move to well that is not on the deck”** | Mistyped well name or wrong labware definition. | Make sure you refer to wells exactly as `plate['A1']` or `plate.wells_by_name()['A1']`. |

---

## 8. Safety & Good‑Laboratory‑Practice notes

* **Biosafety** – Work with the bacterial culture in a BSL‑2 cabinet, wear gloves, and decontaminate the waste with 70 % ethanol or an appropriate disinfectant before discarding.  
* **Antibiotic handling** – Some drugs are hazardous (e.g., β‑lactams, aminoglycosides). Use a fume hood if required and avoid aerosol generation.  
* **Tip disposal** – All used tips must go to the designated bio‑hazard waste bin.  
* **Incubation** – Seal the plate with a breathable plate sealer (e.g., gas‑permeable film) to avoid condensation and ensure proper oxygen exchange.

---

## 9. Quick checklist before running

1. **Prepare reagents**  
   * Sterile broth in reservoir A1 (≥ 1 mL).  
   * Bacterial suspension in reservoir A2 (≈ 1 mL, correct OD).  
   * 2×‑stock antibiotic solutions (100 µL each) in the deep‑well stock plate as described.  
2. **Load the deck exactly as outlined** (tip rack, assay plate, deep‑well plate, reservoir).  
3. **Calibrate the 8‑channel P300** (especially the tip‑offset for 300 µL tips).  
4. **Run a dry‑run** (check the protocol without tips) to ensure the robot’s motions match the layout.  
5. **Start the protocol** – the robot will pause after the liquid‑handling steps so you can seal the plate and put it in the incubator.  

You now have a complete, robot‑ready MIC assay that uses **one 8‑channel pipette, a 96‑well plate, a 12‑well reservoir, a deep‑well stock plate, and a 300 µL tip box**. Adjust the numbers at the top of the script for any future experiment (different drugs, more/less dilution points, different volumes) and you’ll be ready to run dozens of MIC plates with minimal hands‑on time. Happy screening!