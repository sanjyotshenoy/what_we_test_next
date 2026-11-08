# --------------------------------------------------------------
#   OT‑2 Minimum‑Inhibitory‑Concentration (MIC) assay
#   4 antibiotics, 2 replicates, 2‑fold serial dilution (10 points)
# --------------------------------------------------------------
#   Author:  ChatGPT (2026‑11‑08)
#   API level: 2.15
# --------------------------------------------------------------

from opentrons import protocol_api

metadata = {
    'protocolName': 'MIC assay – 4 antibiotics, 2‑replicates, 2‑fold serial dilution',
    'author': 'ChatGPT',
    'description': (
        'Minimum inhibitory concentration test on an OT‑2 using an 8‑channel P300. '
        'Four drugs, each in duplicate, across a 10‑point 2‑fold dilution series. '
        'Columns 1‑10 = dilution series, column 11 = growth control, column 12 = '
        'sterility control.'
    ),
    'apiLevel': '2.15'
}


def run(protocol: protocol_api.ProtocolContext):
    ##################################################################
    # ----------------------  LABWARE & INSTRUMENTS  -----------------
    ##################################################################
    tip_rack_300 = protocol.load_labware(
        'opentrons_96_tiprack_300ul', '1',
        label='300 µL tip rack')

    mic_plate = protocol.load_labware(
        'corning_96_wellplate_360ul_flat', '2',
        label='MIC assay plate')

    antibiotic_stock_plate = protocol.load_labware(
        'nest_96_wellplate_2ml_deep', '3',
        label='Antibiotic 2×‑stock plate')

    reservoir = protocol.load_labware(
        'usascientific_12_reservoir_22ml', '4',
        label='Reagent reservoir')

    # 8‑channel P300 (Gen2).  If you are using a Gen1 instrument, replace the name
    # with 'p300_multi'.
    p300 = protocol.load_instrument(
        'p300_multi_gen2', mount='left', tip_racks=[tip_rack_300])

    # Fixed‑trash well (new name in API ≥ 2.0)
    trash = protocol.fixed_trash.wells()[0]

    ##################################################################
    # -----------------------  USER PARAMETERS  --------------------
    ##################################################################
    # Volumes (µL)
    BROTH_VOLUME = 100          # sterile broth added to every well
    ANTISTOCK_VOLUME = 100      # 2× antibiotic stock added to column 1
    TRANSFER_VOLUME = 100       # volume moved during each dilution step
    BACTERIA_VOLUME = 100       # inoculum added later
    DISCARD_VOLUME = 100        # volume removed after each transfer

    # Plate layout
    N_CONC_COLS = 10             # columns 1‑10 hold the dilution series
    GROWTH_CTRL_COL = 11         # column 11 = growth control (no drug)
    # column 12 (index 11) will be sterility control – no bacteria added

    # --------------------  Reservoir locations  --------------------
    broth = reservoir['A1']      # sterile broth (e.g., CAMHB)
    bacteria = reservoir['A2']   # ~5 × 10⁵ CFU mL⁻¹ bacterial suspension

    # ---------------- Antibiotic‑stock mapping (2 rows per drug) ----------------
    # Each well listed below already contains 100 µL of a 2×‑stock solution.
    stock_map = {
        'drug1': [antibiotic_stock_plate['A1'], antibiotic_stock_plate['B1']],
        'drug2': [antibiotic_stock_plate['C1'], antibiotic_stock_plate['D1']],
        'drug3': [antibiotic_stock_plate['E1'], antibiotic_stock_plate['F1']],
        'drug4': [antibiotic_stock_plate['G1'], antibiotic_stock_plate['H1']],
    }

    ##################################################################
    # -------------------------  STEP 1  ---------------------------
    # Add 100 µL sterile broth to every well.
    ##################################################################
    protocol.comment('STEP 1 – Adding 100 µL sterile broth to all 96 wells.')
    p300.distribute(
        volume=BROTH_VOLUME,
        source=broth,
        dest=[well for well in mic_plate.wells()],
        new_tip='once',
        disposal_volume=0
    )
    # No manual `drop_tip()` needed – `distribute(..., new_tip='once')` drops the tip automatically.

    ##################################################################
    # -------------------------  STEP 2  ---------------------------
    # Add 2× antibiotic stock (100 µL) to column 1 (rows = drug‑specific).
    ##################################################################
    protocol.comment('STEP 2 – Adding 2× antibiotic stock (100 µL) to column 1.')

    # Build an 8‑well list that matches the 8‑channel head order.
    source_wells_col1 = [
        stock_map['drug1'][0],   # tip A → row A (drug 1)
        stock_map['drug1'][1],   # tip B → row B (drug 1)
        stock_map['drug2'][0],   # tip C → row C (drug 2)
        stock_map['drug2'][1],   # tip D → row D (drug 2)
        stock_map['drug3'][0],   # tip E → row E (drug 3)
        stock_map['drug3'][1],   # tip F → row F (drug 3)
        stock_map['drug4'][0],   # tip G → row G (drug 4)
        stock_map['drug4'][1]    # tip H → row H (drug 4)
    ]

    dest_wells_col1 = mic_plate.columns()[0]      # A1‑H1 (8 wells)

    p300.transfer(
        volume=ANTISTOCK_VOLUME,
        source=source_wells_col1,
        dest=dest_wells_col1,
        new_tip='once',
        mix_before=(3, 50),      # gentle pre‑mix of each stock well
        mix_after=(3, 50),       # ensure the destination is well mixed
        blow_out=True
    )
    # Again, the tip is dropped automatically – no extra `drop_tip()`.

    ##################################################################
    # -------------------------  STEP 3  ---------------------------
    # Remove the extra 100 µL from column 1 so that each well holds 100 µL.
    ##################################################################
    protocol.comment('STEP 3 – Removing the extra 100 µL from column 1 (waste).')
    p300.pick_up_tip()
    for well in dest_wells_col1:
        p300.aspirate(DISCARD_VOLUME, well)
        p300.dispense(DISCARD_VOLUME, trash)
    p300.drop_tip()

    ##################################################################
    # -------------------------  STEP 4  ---------------------------
    # 2‑fold serial dilution across columns 1‑10 (discard the extra volume each time).
    ##################################################################
    protocol.comment('STEP 4 – Performing 2‑fold serial dilution (columns 1→10).')
    p300.pick_up_tip()
    for src_idx in range(N_CONC_COLS - 1):            # src = col 1‑9, dest = col 2‑10
        src_col = mic_plate.columns()[src_idx]       # list of 8 source wells
        dest_col = mic_plate.columns()[src_idx + 1]  # list of 8 destination wells

        # 1️⃣ Transfer 100 µL from source → destination (keeps tip attached)
        p300.transfer(
            volume=TRANSFER_VOLUME,
            source=src_col,
            dest=dest_col,
            new_tip='never',
            mix_before=(3, 50),
            mix_after=(3, 50),
            blow_out=True
        )

        # 2️⃣ Discard the extra 100 µL from the *destination* column back to trash
        for well in dest_col:
            p300.aspirate(DISCARD_VOLUME, well)
            p300.dispense(DISCARD_VOLUME, trash)
    p300.drop_tip()   # tip used for the whole dilution series is now discarded

    ##################################################################
    # -------------------------  STEP 5  ---------------------------
    # Add bacterial inoculum (100 µL) to columns 1‑11.
    ##################################################################
    protocol.comment(
        'STEP 5 – Adding bacterial suspension (100 µL) to test columns '
        'and the growth‑control column (column 11).'
    )
    # Columns 1‑10 (indices 0‑9) + column 11 (index 10) receive bacteria.
    for col_idx in range(N_CONC_COLS + 1):   # 0‑10 → columns 1‑11
        dest_col = mic_plate.columns()[col_idx]
        p300.transfer(
            volume=BACTERIA_VOLUME,
            source=bacteria,
            dest=dest_col,
            new_tip='always',   # fresh tip for each column prevents cross‑contamination
            blow_out=True
        )
    # Column 12 (sterility control) stays broth‑only – no bacteria added.

    ##################################################################
    # ---------------------------  FINISH  -------------------------
    ##################################################################
    protocol.comment(
        'All liquids are now in place.  Seal the plate, incubate (e.g. '
        '18‑20 h at 35‑37 °C), then read OD600 or your chosen endpoint.'
    )
    protocol.pause(
        'Plate is ready for sealing & incubation.  Press RESUME when you are '
        'ready to finish the protocol.'
    )
