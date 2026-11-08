metadata = {
    'protocolName': 'MIC 2-fold broth microdilution - 4 antibiotics x 2 replicates (8-channel only)',
    'apiLevel': '2.13'
}

def run(protocol):
    # ---------------- Labware ----------------
    tips_multi  = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    plate       = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    reservoir   = protocol.load_labware('usascientific_12_reservoir_22ml', 5)
    stock_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6)

    m300 = protocol.load_instrument('p300_multi_gen2', 'left',
                                    tip_racks=[tips_multi])

    # ---------------- Reservoir / stock plate assignments ----------------
    media    = reservoir['A1']     # cation-adjusted MHB, load >= 6 mL
    bacteria = reservoir['A6']      # 2x inoculum (~1e6 CFU/mL), load >= 6 mL
    waste    = reservoir['A12']

    # Stock plate column 1 mirrors assay plate column 1:
    #   A1,B1 = Antibiotic 1 | C1,D1 = Antibiotic 2
    #   E1,F1 = Antibiotic 3 | G1,H1 = Antibiotic 4
    # Each well loaded with >= 200 uL of 2x stock.
    abx_stock_col = stock_plate['A1']   # one well -> multichannel acts on A1..H1

    VOL_MEDIA    = 50   # uL media into cols 2-12
    VOL_SEED     = 100  # uL antibiotic stock into col 1
    VOL_TRANSFER = 50   # uL serial dilution transfer
    VOL_BACT     = 50   # uL inoculum into all wells

    cols = plate.columns()

    # ---------------- STEP 1: media into columns 2-12 ----------------
    m300.pick_up_tip()
    media_cols = cols[1:]                              # columns 2..12
    for i in range(0, len(media_cols), 4):
        batch = media_cols[i:i + 4]
        m300.aspirate(VOL_MEDIA * len(batch), media.bottom(2))
        for col in batch:
            m300.dispense(VOL_MEDIA, col[0])           # well A -> whole column
    m300.blow_out(media.top())
    m300.drop_tip()

    # ---------------- STEP 2: seed column 1 from the stock plate ----------------
    # Each channel aspirates its OWN antibiotic from its own stock well,
    # then dispenses into the matching assay-plate row.
    m300.pick_up_tip()
    m300.aspirate(VOL_SEED, abx_stock_col.bottom(3))
    m300.dispense(VOL_SEED, plate['A1'].bottom(5))
    # Tips are NOT dropped here: each channel's tip has only ever touched
    # its own antibiotic, so they are reused for the first dilution
    # transfer (this keeps total tip usage at exactly 96).

    # ---------------- STEP 3: 2-fold serial dilution, columns 1 -> 11 ----------------
    for i in range(10):
        if i > 0:
            m300.pick_up_tip()                          # fresh tips per transfer
        src = cols[i][0]
        dst = cols[i + 1][0]

        m300.aspirate(VOL_TRANSFER, src)
        m300.dispense(VOL_TRANSFER, dst)

        # mix destination column 3 x 50 uL
        for _ in range(3):
            m300.aspirate(VOL_TRANSFER, dst)
            m300.dispense(VOL_TRANSFER, dst)

        if i == 9:
            # remove excess 50 uL from column 11 to normalize volume
            m300.aspirate(VOL_TRANSFER, dst)
            m300.dispense(VOL_TRANSFER, waste)

        m300.drop_tip()

    # ---------------- STEP 4: inoculate all 96 wells ----------------
    m300.pick_up_tip()

    # gently resuspend inoculum in the trough before dispensing
    for _ in range(3):
        m300.aspirate(100, bacteria.bottom(5))
        m300.dispense(100, bacteria.bottom(5))

    for i in range(0, 12, 4):
        batch = cols[i:i + 4]
        m300.aspirate(VOL_BACT * len(batch), bacteria.bottom(2))
        for col in batch:
            m300.dispense(VOL_BACT, col[0])

    m300.drop_tip()
