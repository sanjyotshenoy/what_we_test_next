metadata = {
    'protocolName': 'MIC 2-fold broth microdilution - 4 antibiotics x 2 replicates (fixed)',
    'apiLevel': '2.13'
}

def run(protocol):
    # ---------------- Labware ----------------
    tips_multi  = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    tips_single = protocol.load_labware('opentrons_96_tiprack_300ul', 6)
    plate       = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    reservoir   = protocol.load_labware('usascientific_12_reservoir_22ml', 5)

    m300 = protocol.load_instrument('p300_multi_gen2', 'left',
                                    tip_racks=[tips_multi])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips_single])

    # ---------------- Reservoir assignments ----------------
    media     = reservoir['A1']                      # cation-adjusted MHB
    abx_stock = [reservoir['A2'], reservoir['A3'],   # 2x stocks
                 reservoir['A4'], reservoir['A5']]
    bacteria  = reservoir['A6']                       # ~1e6 CFU/mL (2x inoculum)
    waste     = reservoir['A12']

    # Rows per antibiotic: A/B = Abx1, C/D = Abx2, E/F = Abx3, G/H = Abx4
    abx_rows = [['A', 'B'], ['C', 'D'], ['E', 'F'], ['G', 'H']]

    VOL_MEDIA    = 50   # uL media into cols 2-12
    VOL_SEED     = 100  # uL antibiotic stock into col 1
    VOL_TRANSFER = 50   # uL serial dilution transfer
    VOL_BACT     = 50   # uL inoculum into all wells

    cols = plate.columns()

    # ---------------- STEP 1: media into columns 2-12 ----------------
    # 11 columns x 50 uL. One tip column; aspirate 200 uL, feed 4 columns per trip.
    m300.pick_up_tip()
    media_cols = cols[1:]                              # columns 2..12
    for i in range(0, len(media_cols), 4):
        batch = media_cols[i:i + 4]
        m300.aspirate(VOL_MEDIA * len(batch), media.bottom(2))
        for col in batch:
            m300.dispense(VOL_MEDIA, col[0])           # well A of column -> whole column
    m300.blow_out(media.top())
    m300.drop_tip()

    # ---------------- STEP 2: seed column 1 with 2x antibiotic stocks ----------------
    for stock, rows in zip(abx_stock, abx_rows):
        p300.pick_up_tip()
        p300.aspirate(VOL_SEED * 2, stock.bottom(2))
        for r in rows:
            p300.dispense(VOL_SEED, plate[r + '1'].bottom(5))
        p300.drop_tip()

    # ---------------- STEP 3: 2-fold serial dilution, columns 1 -> 11 ----------------
    # Fresh tip column for every transfer step (prevents carryover between
    # antibiotics). Multichannel acts on a whole column when given one well.
    for i in range(10):
        m300.pick_up_tip()
        src = cols[i][0]
        dst = cols[i + 1][0]

        m300.aspirate(VOL_TRANSFER, src)
        m300.dispense(VOL_TRANSFER, dst)

        # mix destination well 3 x 50 uL
        for _ in range(3):
            m300.aspirate(VOL_TRANSFER, dst)
            m300.dispense(VOL_TRANSFER, dst)

        if i == 9:
            # last step: remove excess 50 uL from column 11 to normalize volume
            m300.aspirate(VOL_TRANSFER, dst)
            m300.dispense(VOL_TRANSFER, waste)

        m300.drop_tip()

    # ---------------- STEP 4: inoculate all 96 wells ----------------
    # 12 columns x 50 uL. One tip column; aspirate 200 uL, feed 4 columns per trip.
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
