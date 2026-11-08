metadata = {
    'protocolName': 'MIC 2-fold broth microdilution - 4 antibiotics x 2 replicates',
    'apiLevel': '2.13'
}

def run(protocol):
    # ---------- Labware ----------
    tips_multi   = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    tips_single  = protocol.load_labware('opentrons_96_tiprack_300ul', 6)
    plate        = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    reservoir    = protocol.load_labware('usascientific_12_reservoir_22ml', 5)

    m300 = protocol.load_instrument('p300_multi_gen2', 'left',
                                    tip_racks=[tips_multi])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips_single])

    # ---------- Reservoir assignments ----------
    media     = reservoir['A1']
    abx_stock = [reservoir['A2'], reservoir['A3'],
                 reservoir['A4'], reservoir['A5']]
    bacteria  = reservoir['A6']
    waste     = reservoir['A12']

    # Rows per antibiotic: A/B = Abx1, C/D = Abx2, E/F = Abx3, G/H = Abx4
    abx_rows = [['A', 'B'], ['C', 'D'], ['E', 'F'], ['G', 'H']]

    VOL_MEDIA    = 50   # µL into cols 2-12
    VOL_SEED     = 100  # µL antibiotic stock into col 1
    VOL_TRANSFER = 50   # µL serial dilution transfer
    VOL_BACT     = 50   # µL inoculum into all wells

    cols = plate.columns()

    # ---------- Step 1: media into columns 2-12 ----------
    m300.pick_up_tip()
    media_dests = [w for col in cols[1:] for w in col]
    m300.distribute(VOL_MEDIA, media.bottom(2), media_dests,
                    disposal_volume=20)
    m300.drop_tip()

    # ---------- Step 2: seed column 1 with 2x antibiotic stocks ----------
    for stock, rows in zip(abx_stock, abx_rows):
        p300.pick_up_tip()
        p300.aspirate(VOL_SEED * 2, stock.bottom(2))
        for r in rows:
            p300.dispense(VOL_SEED, plate[r + '1'].bottom(5))
        p300.blow_out(waste)
        p300.drop_tip()

    # ---------- Step 3: 2-fold serial dilution across columns 1 -> 11 ----------
    for i in range(10):
        m300.pick_up_tip()
        m300.transfer(VOL_TRANSFER, cols[i], cols[i + 1],
                      mix_after=(3, 40),      # 3x 40 µL mix in destination
                      touch_tip=True,
                      new_tip='never')
        if i < 9:
            m300.drop_tip()
        else:
            # Remove excess 50 µL from column 11 to normalize volume
            m300.aspirate(VOL_TRANSFER, cols[10])
            p300_none = None
            m300.dispense(VOL_TRANSFER, waste)
            m300.drop_tip()

    # ---------- Step 4: inoculate all wells with bacteria ----------
    m300.pick_up_tip()
    all_wells = [w for col in cols for w in col]
    m300.distribute(VOL_BACT, bacteria.bottom(2), all_wells,
                    disposal_volume=20)
    m300.drop_tip()
