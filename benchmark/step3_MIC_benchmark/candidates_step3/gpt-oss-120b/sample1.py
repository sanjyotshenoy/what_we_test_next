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
