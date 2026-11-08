from opentrons import protocol_api

metadata = {
    "protocolName": "MIC_4Abx_2Replicates_1Plate_200uL",
    "author": "CL_Bridges Lab_CMU",
    "description": "CLSI 100 + 100 uL broth microdilution: 4 antibiotics, 2 replicate "
                   "rows each (A+E, B+F, C+G, D+H), one plate, sparse antibiotic tips, "
                   "fresh tips for every bacteria column.",
}

requirements = {"robotType": "OT-2", "apiLevel": "2.28"}

# ---------------------------------------------------------------------------
# Settings (edit here)
# ---------------------------------------------------------------------------
BROTH_VOL = 100            # uL broth in columns 2-11
STERILITY_VOL = 200        # uL broth in column 12
ANTIBIOTIC_VOL = 200       # uL antibiotic (2x top concentration) into column 1
DILUTION_VOL = 100         # uL moved column to column
BACTERIA_VOL = 100         # uL inoculum (2x final density) into columns 1-11
MIX_VOL = 150              # uL mix volume (wells hold 200 uL while mixing)
MIX_REPS = 3
PAUSE_BEFORE_BACTERIA = True   # pause so the inoculum is loaded fresh

# Antibiotic -> (reservoir well, slot 6 tip-rack column, plate rows it ends up in)
# Every antibiotic step targets plate row A with the 8-channel pipette. Which rows
# actually receive liquid is decided by where the 2 tips sit in that tip column.
ANTIBIOTICS = [
    ("Antibiotic 1", "A2", "A2", "A + E"),   # tips in rows A and E of tip column 2
    ("Antibiotic 2", "A3", "A3", "B + F"),   # tips in rows B and F of tip column 3
    ("Antibiotic 3", "A4", "A4", "C + G"),   # tips in rows C and G of tip column 4
    ("Antibiotic 4", "A5", "A5", "D + H"),   # tips in rows D and H of tip column 5
]


def run(protocol: protocol_api.ProtocolContext) -> None:
    # Turn on the OT-2 rail lights so the deck is lit for the whole run
    protocol.set_rail_lights(True)

    # -----------------------------------------------------------------------
    # Labware
    # -----------------------------------------------------------------------
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", "6")
    tips_9 = protocol.load_labware("opentrons_96_tiprack_300ul", "9")   # extra bacteria tips
    reservoir = protocol.load_labware("usascientific_12_reservoir_22ml", "3")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "5", label="P1")
    trash = protocol.fixed_trash

    # -----------------------------------------------------------------------
    # Pipette (8-channel; tip columns are addressed explicitly, not auto-assigned)
    # -----------------------------------------------------------------------
    p300 = protocol.load_instrument("p300_multi", "left")
    p300.flow_rate.aspirate = 150
    p300.flow_rate.dispense = 300
    p300.well_bottom_clearance.aspirate = 1   # mm above well bottom
    p300.well_bottom_clearance.dispense = 1

    # -----------------------------------------------------------------------
    # Liquids (for the Opentrons App deck map)
    # -----------------------------------------------------------------------
    broth = protocol.define_liquid("Broth (CAMHB)", display_color="#ff9900")
    bacteria = protocol.define_liquid("Bacteria, ~1e6 CFU/mL", display_color="#0517c2")
    abx_colors = ["#cf0d0d", "#7030a0", "#00897b", "#c77800"]

    reservoir["A1"].load_liquid(liquid=broth, volume=12000)
    for (name, res_well, _tip_col, _plate_rows), color in zip(ANTIBIOTICS, abx_colors):
        liq = protocol.define_liquid(f"{name}, 2x top concentration", display_color=color)
        reservoir[res_well].load_liquid(liquid=liq, volume=2000)
    reservoir["A6"].load_liquid(liquid=bacteria, volume=12000)

    broth_src = reservoir["A1"]
    bact_src = reservoir["A6"]
    col_a = plate.rows_by_name()["A"]   # col_a[0] = column 1 ... col_a[11] = column 12

    # =======================================================================
    # Step 1 - Broth into columns 2-11, then column 12
    # Tip-rack column 1 (all 8 tips: broth goes into all 8 rows)
    # =======================================================================
    p300.pick_up_tip(tips["A1"])
    for dest in col_a[1:11]:
        p300.aspirate(BROTH_VOL, broth_src)
        p300.dispense(BROTH_VOL, dest)
    p300.aspirate(STERILITY_VOL, broth_src)
    p300.dispense(STERILITY_VOL, col_a[11])
    p300.drop_tip()

    # =======================================================================
    # Step 2 - For each antibiotic: load column 1 and run its dilution series
    # Tip-rack columns 2-5 (2 tips each, in rows A+E, B+F, C+G, D+H)
    # The same tips load the antibiotic, dilute it and mix it.
    # =======================================================================
    for name, res_well, tip_col, plate_rows in ANTIBIOTICS:
        protocol.comment(f"--- {name}: reservoir {res_well} -> plate rows {plate_rows} ---")
        p300.pick_up_tip(tips[tip_col])

        # 2a. 200 uL antibiotic into column 1 (only the 2 channels with tips carry liquid)
        p300.mix(1, ANTIBIOTIC_VOL, reservoir[res_well])          # pre-wet
        p300.aspirate(ANTIBIOTIC_VOL, reservoir[res_well])
        p300.dispense(ANTIBIOTIC_VOL, col_a[0])

        # 2b. 2-fold serial dilution, column 1 -> column 10
        for c in range(9):                                        # col_a[0] = column 1
            p300.aspirate(DILUTION_VOL, col_a[c])
            p300.dispense(DILUTION_VOL, col_a[c + 1])
            p300.mix(MIX_REPS, MIX_VOL, col_a[c + 1])

        # 2c. discard the surplus 100 uL so every column holds 100 uL
        p300.aspirate(DILUTION_VOL, col_a[9])
        p300.dispense(DILUTION_VOL, trash)
        p300.drop_tip()

    # =======================================================================
    # Optional pause: load / resuspend the inoculum in reservoir A6
    # =======================================================================
    if PAUSE_BEFORE_BACTERIA:
        protocol.pause("Load or resuspend the bacterial inoculum (~1e6 CFU/mL) in "
                       "reservoir A6, then click Resume. Use it within 15 min of "
                       "preparation.")

    # =======================================================================
    # Step 3 - 100 uL bacteria into columns 1-11
    # A FRESH column of 8 tips for every plate column, so no tip that touched
    # antibiotic ever goes back into the bacteria trough or into another column.
    # Tips: slot 6 columns 6-12, then slot 9 columns 1-4 (11 tip columns, 88 tips).
    # Filled from column 11 down to column 1 (lowest antibiotic first).
    # =======================================================================
    bact_tip_cols = ([tips[f"A{c}"] for c in range(6, 13)] +
                     [tips_9[f"A{c}"] for c in range(1, 5)])
    for dest, tip_col in zip(reversed(col_a[0:11]), bact_tip_cols):
        p300.pick_up_tip(tip_col)
        p300.mix(1, BACTERIA_VOL, bact_src)                       # pre-wet / resuspend
        p300.aspirate(BACTERIA_VOL, bact_src)
        p300.dispense(BACTERIA_VOL, dest)
        p300.mix(MIX_REPS, MIX_VOL, dest)
        p300.drop_tip()
