The user wants a protocol design for an MIC (minimum inhibitory concentration) test on the OT-2. Let me think about layout and protocol structure.

Setup: 4 antibiotics × 2 replicates = 8 columns needed... Actually typical MIC broth microdilution: 2-fold serial dilution of antibiotic across columns, then inoculate with bacteria. 96-well plate = 8 rows × 12 columns.

Design options: Each antibiotic gets one row (or column) per replicate. 4 antibiotics × 2 replicates = 8 strips. With 8 rows (A–H), perfect: each row = one antibiotic replicate, 2-fold dilution across 12 columns (column 1 highest concentration, column 11 lowest, column 12 = growth control? Actually 11 dilutions + 1 control).

Column-wise or row-wise? Serial dilution across columns (1→11) with column 12 as growth control (no antibiotic). 8-channel pipette works well along columns (rows A–H simultaneously), which is good since all 8 rows have the same dilution step — column-wise serial dilution with multichannel pipette: transfer from column to column across all rows simultaneously. That's efficient.

Protocol:
1. Plate setup: fill columns 2–12 (or all) with media (e.g., 100 µL cation-adjusted MHB).
2. Add antibiotic at 2× highest concentration to column 1 (100 µL each well in relevant rows... wait, each row is a different antibiotic!). Hmm — if rows are different antibiotics, then adding antibiotic to column 1 of each row requires single-channel additions of 4 different antibiotics. That's fine — 8 wells to fill manually or via single channel.

Alternative: use columns for antibiotics (each antibiotic replicate = one column of 12? No, dilution goes down a column then... 8 wells per column only gives 8 dilutions).

Better layout: antibiotics in rows. Row A & B: Abx 1; C&D: Abx 2; E&F: Abx 3; G&H: Abx 4. Dilution across columns 1–11, column 12 = growth control (media + bacteria, no antibiotic).

Steps:
1. Load labware: tiprack (300 µL), reservoir, plate, all on deck. OT-2 with GEN2 8-channel P300.
2. Dispense media into columns 2–12 (100 µL per well) using 8-channel from reservoir media slot.
3. Dispense 100 µL of 2× antibiotic stock into column 1 rows A–H (single channel or 8-channel? Different antibiotics per row — single channel picks from different reservoir slots; or use one-tip-across approach. Simplest: single channel additions, 2 wells per antibiotic = 8 total dispenses).
4. Serial dilution: 8-channel, transfer 100 µL from column 1 → 2, mix, column 2 → 3, ... column 10 → 11, discard 100 µL from column 11 (to waste/reservoir waste slot). Mixing at each step (e.g., 3–5 aspiration/dispense cycles). New tips optional; use same tips for dilution if acceptable (carryover is same antibiotic across row—each row has different antibiotic though! Same tips across all 8 rows would carryover antibiotic 1 into antibiotic 2 rows!). Important: change tips between serial dilution transfers OR accept carryover? No — must change tips each column transfer. 10 transfers × tip change. Or do the dilution with tip change per column: fine, 10 columns of fresh tips.

Actually with carryover: tips touch row A (Abx1), then row H (Abx4) — cross contamination. So change tips for each column-to-column transfer. 300 µL tip rack has 96 tips, 8 channels use 8 tips per pickup → 12 pickups possible. Need 10 (cols 1→2 through 10→11) + maybe reserve. Tight but doable if media dispensing uses... media dispensing with 8-channel uses 8 tips per column pickup? Dispensing same media into 11 columns = 11 pickups × 8 tips = 88 tips. Plus 10 for dilution = 98 > 96. Need two tip racks or reuse strategy.

Better: use one set of tips for media dispensing (same liquid, no contamination — fine to reuse tips for same media), then new tips for dilution steps (10 pickups). That works with one 300 µL rack if media uses 1 pickup set... but fresh tips for dilution: 10 pickups × 8 = 80, plus media 8 = 88 ≤ 96. OK, one rack works if media tips are reused across columns.

Hmm, but reservoir slots: media, Abx1–4, bacteria, waste = 7 slots. Standard 12-channel reservoir (single channel has 12 wells) or a 6-slot... need 7 slots. Use a 12-well reservoir (e.g., USA Scientific 12-channel or Agilent 1-channel 12 reservoir... Opentrons' "agilent_1_reservoir_290ml" is 1 well. Use "usascientific_12_reservoir_22ml" — 12 channels, perfect.

Bacteria: standardized inoculum (0.5 McFarland, diluted) in reservoir; add 100 µL to all wells (2× final... wait). Standard CLSI: final volume 100 µL/well with antibiotic 2× concentrated then bacteria... Actually classical: 100 µL antibiotic dilution in broth + 10 µL inoculum, or 50+50. Simpler robot approach: prepare everything at 2× then add equal volume bacteria to get 1×. Let's do: columns filled with 100 µL of antibiotic serial dilution at 2× (after dilution, col 1–11 contain 2× concentrations since we made them from 2× stock diluted in media... wait serial dilution with media gives concentrations halving starting from stock concentration in column 1). If stock is 2× the desired highest conc, then after adding 100 µL bacteria at 2× inoculum, everything dilutes to 1×. Final volume 200 µL per well. That's a common approach and volume-friendly.

Alternative simpler: 100 µL per well total, add 95 µL antibiotic dilutions + 5 µL inoculum. But robot-wise, 2× approach is easier.

So:
- Media into cols 2–12: 50 µL each (since final 2× system). Let's define: col 1: 100 µL antibiotic stock (2× highest). Cols 2–12: 50 µL media. Serial: transfer 50 µL col1→col2 (now 100 µL at half conc), mix... then col2→3 etc. Hmm, that makes each column after transfer 100 µL with proper halving: col1 has 100, transfer 50 to col2 (col2: 50 media + 50 = 100 at 1/2 conc). Then col2→3 50 µL, col2 remains 50 µL. Ends: col 11 has 100 µL, discard 50 from col 11 → 50 µL at 1/2048× ... then all columns have 50 µL at 2× concentrations, add 50 µL bacteria at 2× inoculum → 100 µL final at 1×. Wait, col 12 is growth control: 50 µL media only, gets 50 µL bacteria.

So volumes: media 50 µL into cols 2–12; col 1: 100 µL 2× antibiotic stock... wait final should be consistent: col 1 final 100 µL needs 50 µL antibiotic + 50 µL bacteria. Col1: add 100 µL antibiotic stock (2× conc = final highest×2). Serial: take 50 from col1 → col2. Col1 left with 50 µL at full 2× conc. Col2: 50 media + 50 = 100 µL at 1× 2× conc... hmm 2× conc halved. Then 50 from col2 → col3, col2 left 50 µL. Continue to col11: after transfer in, col11 = 100 µL, remove 50 (discard). All cols 1–11 = 50 µL at 2× concentrations. Col 12 = 50 µL media. Then 50 µL bacteria everywhere. 

Bacteria dispensing: 8-channel, 12 columns, one set of tips (same bacteria suspension, reuse tips fine). Column 12 becomes growth control. Could also do sterility control? Not requested; could note that all 96 wells get bacteria so no sterility blank — mention as an option to reserve a column or use edge... Actually 4 antibiotics × 2 reps uses all 8 rows across 12 columns = full plate. Growth control col 12 included. Sterility/media blank would need a 9th row or a separate plate — mention briefly.

Deck layout:
- Slot 1: 300 µL tip rack
- Slot 2: 96-well plate (e.g., Nunc/Sarstedt; recommend a standard flat-bottom plate)
- Slot 3: reservoir (12-channel)
- Slot 4: second tip rack optional / waste reservoir for discarding dilution volume (can use reservoir waste slot)

Pipette: GEN2 P300 8-channel mounted on left (multi-channel must go on left? On OT-2, multichannel on right can crash? No—OT-2 supports either, but multichannel traditionally left. Actually OT-2: 8-channel can be on either mount but left is typical. Keep left.)

Concentration scheme example: e.g., highest conc 1024 µg/mL → range 1024–1 µg/mL over 11 columns (2^10 = 1024-fold). 

Serial dilution tips: change tips between each column transfer (10 pickups of 8 tips = 80 tips). Plus media 8 (reused), antibiotic additions single-channel — same 8-channel pipette can use single row? 8-channel picks a full column of tips; single well dispensing wastes tips. Alternative: add antibiotics with the 8-channel... can't reach individual rows with a full 8-channel easily — actually it can: position over a single row using the top channel; Opentrons supports picking single tips from column of rack by moving? No — 8-channel picks 8 tips; you can dispense to a single well by offsetting, but tips remain. Simpler: use 8-channel to aspirate each antibiotic from its reservoir slot individually? An 8-channel over a reservoir trough spans the whole trough (troughs are designed for multichannel). It can't aspirate from one part... it can — the 8-channel can aspirate from a reservoir with tips in just... no, all 8 tips aspirate.

Option: dedicate a fresh tip column: pick 8 tips with 8-channel, but that's clunky. Cleanest: dispense antibiotics via single-channel logic using the 8-channel in a "use one tip" mode? Opentrons Python API: you can do pipette.pick_up_tip at specific locations — with a multichannel you can't pick a single tip (it picks a whole column). But you CAN use `pipette.aspirate` at a single well location while holding 8 tips — liquid only enters the one tip at that position if the well is aligned with one of the tips. Hmm, actually people do this: move multichannel so its back channel is over a well, aspirate — only that tip takes liquid. It works but is hacky and wastes 8 tips.

Simplest practical: 8 antibiotic additions to column 1 (2 wells per antibiotic, rows A/B, C/D, E/F, G/H). Use a single-channel pipette if available (P300 single on right mount) — but user only listed 8-channel. Alternative: put antibiotics in reservoir slots and use the multichannel trick, or just do 2 pickups: pick 8 tips, use channel-A tip? Eh.

Cleanest with only 8-channel: Aspirate antibiotic 1 with... Actually another approach: since column 1 addition is 100 µL to 2 wells (rows A & B), use the multichannel positioned so one tip aligns over well A1, aspirate 200 µL (enough for both wells + overage), dispense 100 to A1, move to B1, dispense 100. Then for antibiotic 2, new tips... The API supports aspirating with specific tip of multichannel by using `well.top()` offsets — commonly done via `pipette.aspirate(volume, location)` where location is a single well; all 8 tips go down but only the one over the well... no, all 8 tips would be in liquid if over a trough; over a 96-well plate only the aligned tip enters the well. For reservoir it's a trough — problem.

Pragmatic recommendation: this is a known pattern; many Opentrons MIC protocols use the multichannel and just do the antibiotic seeding differently: seed antibiotics using 8-channel by dispensing to column 1 with tips from... I'll just write the protocol with a helper that uses the multichannel to pick up a column of tips, and dispense antibiotic to rows using single-tip alignment over the plate? Antibiotics are in reservoir troughs though — aspirating from a trough with 8 tips means all 8 aspirate.

Better idea: put antibiotics in a 96-well deep-well plate or use single tips. OR: reorient plate so antibiotics go down columns? If each antibiotic replicate occupies a column and dilution goes down rows... only 8 rows = 8 dilutions, plate is 8 rows. Dilution across 12 columns gives 11 concentrations — better.

Alternative clean solution: use fresh tips per antibiotic, and use the "use only one channel" approach by aspirating from the reservoir at an offset? Troughs are wide; 8 tips across... Opentrons 8-channel tips span 9mm×8 = 63mm; trough width ~ typical 12-reservoir channel width ~ 13mm? Not enough.

Realistic answer: recommend two pipettes (single + multi) OR do antibiotic seeding manually/manually preloading column 1. OR use a deep well plate for antibiotics sources. Given the user's labware list, I can suggest adding a single-channel pipette for the seeding step, or restructure: dispense antibiotic stock to column 1 using 4 fresh tip-columns: pick 8 tips, aspirate 100 µL per tip... you could aspirate all four antibiotics at once! Pick up 8 tips, aspirate Abx1 into the top tip? No—can't control individual tips in trough.

Hmm, actually there IS a well-known trick: `pipette.aspirate` at a specific well of a plate-like labware with a multichannel — the API allows `pipette.aspirate(vol, plate['A1'])` and the back channel takes liquid if positioned. But trough: all channels submerged.

Decision: I'll recommend the antibiotics be placed in wells of the 12-channel reservoir — 12-reservoir plate channels are separate wells (like the USA Scientific 12-channel, each channel ~13mm wide but separate). An 8-channel over one channel of the reservoir — tips span 63mm, channels separated by plastic? The usascientific 12-reservoir has 12 separate troughs each about... width ~ 8-9mm? The 8 tips would span multiple troughs. Not workable.

Simplest robust: load antibiotics in a deep well plate / or use a second tip rack and a single-channel pipette. Since user may want minimal, I'll present: seed column 1 with antibiotics using the 8-channel pipette in "single-tip mode" is unreliable; instead recommend either (a) add a P300 single-channel pipette, or (b) pre-load the 2× antibiotic stocks into column 1 of the plate manually / with single channel, or (c) place antibiotic stocks into a 96-well source plate.

Actually wait — another elegant option: use the reservoir for antibiotics but dispense with the 8-channel by aspirating antibiotic with all 8 tips from the trough and dispensing to... no, rows A–H are different antibiotics.

Hmm, alternative layout that solves this: swap rows/columns! Put antibiotics in COLUMNS and dilutions down ROWS... only 8 rows. 4 abx × 2 reps = 8 columns (A–H down... columns 1–8?), dilution down the column = 8 wells = 7 dilutions + control. Loses dilution range.

Or: dilution across columns 1–11 but antibiotics arranged by row requires different antibiotics in same column — inherently row-based seeding.

OK here's another thought: we can seed column 1 with the 8-channel by doing it antibiotic pair by antibiotic pair using... single tips are the issue.

Actually — Opentrons multichannel CAN pick up a single tip? No. But you CAN use `pipette.pick_up_tip(tiprack.rows()[0][0])`? With multichannel this picks a column of tips.

Final approach: I'll design the protocol to include a P300 Single as recommended addition for the seeding step, but also offer fallback: seeding column 1 manually or pre-loading with a multichannel-compatible trick where antibiotics are placed in a 96-well plate (e.g., column of a deep-well plate or even a small "stock plate"): place each 2× antibiotic stock in wells of a deep well plate (e.g., 2 mL deep-well plate, 4 wells), then 8-channel can aspirate from one well (one tip aligned) — works if deep-well plate loaded. But again same issue as aspirating single tip over plate well: yes this WORKS! If antibiotic stocks are in a 96-well (deep-well) plate at positions, an 8-channel with 8 tips can move so that ONE tip is over the source well and aspirate — actually all 8 tips would be at same height over adjacent empty wells; only the one in the source well aspirates. This is a real technique used in Opentrons protocols. However liquid volumes: aspirating 200+ µL into one tip of a multichannel is fine.

But dispensing to A1 and B1: move so bottom tip over A1 dispense, then over B1 dispense. Yes this works and uses only 8 tips total for all 4 antibiotics (reusing same tip set: tip 1 carried Abx1, tip 2 carried Abx2... contamination between antibiotics! Tip that dispensed Abx1 into A1 then used for Abx2 into C1 — carryover. Need tip change per antibiotic, or use 8 different tips — pick 8 tips, use bottom tip for Abx1→A1,B1; second tip for Abx2→C1,D1... but the multichannel aspirates with whichever tip is over the well. So use tip 1 (bottom) for Abx1 wells, tip 2 for Abx2, etc. Aspirate Abx1 into bottom tip by positioning bottom tip over Abx1 stock well, dispense. Then move up one tip position for Abx2 (tip 2 over stock well). All 8 tips used, each carries its own antibiotic, no cross-contamination. Clever but fiddly to explain; position math: the pipette position = well position + tip offset.

Given complexity, my recommendation: simplest reliable = have the antibiotic stocks in reservoir slots, and perform seeding with 4 fresh tip-columns? No...

You know, let me just go with the cleanest widely-used design and be honest about the constraint:

Design choice: Use a 12-channel reservoir with media in a big slot; antibiotics and bacteria also in reservoir. For seeding column 1 (rows A–H), note that the 8-channel pipette can't dispense different liquids to different rows in one pass — so do it in 4 passes, one antibiotic at a time, using a single tip via the "backchannel" trick? For aspirating from trough — all 8 tips aspirate from trough if submerged. But you can position so only ONE tip enters the trough? Troughs are ~13mm wide for 12-channel reservoirs... actually the usascientific_12_reservoir_22ml has channels ~ 12mm? 8 tips span 63mm — many tips would enter neighboring channels. Aspirating 8 tips from adjacent channels = mixing antibiotics. Bad.

Alternative that's actually standard: put the 2× antibiotic stocks directly into column 1 rows... no wait, we could dispense using single tips if we add a single-channel pipette. I'll include: "Add a P300 single-channel (GEN2) on the right mount" OR "pre-load antibiotic stocks into column 1 of a 2 mL deep-well plate, use 8-channel with single-tip positioning."

Hmm, actually — one more option, the simplest of all: do the serial dilution FIRST (media everywhere, serial dilute), then add antibiotics? No, dilution requires antibiotic present.

Alternatively restructure the assay: 2× antibiotics seeded into column 1 — could be done by the robot with a single channel if we just accept 8 slow single-channel aspirations. If only the 8-channel exists, honestly the standard solution in the Opentrons community: use the 8-channel and pick up tips only in a "single tip" fashion is impossible; so protocols like the "Antibiotic serial dilution" template from Opentrons use... The Opentrons " broth microdilution MIC" protocols I recall use both a single and multi channel. 

Decision: I'll present the protocol with a recommended two-pipette setup (P300 single + P300 8-channel) and note that if only the 8-channel is available, the antibiotic seeding into column 1 can be done manually (it's only 8 wells) or by loading stocks into a deep-well plate. That's practical and honest.

Actually, wait — maybe I can restructure to avoid the problem entirely! What if the antibiotics are seeded along a COLUMN instead? I.e., rotate the assay: each antibiotic replicate occupies a column... dilution down rows = max 8 dilutions. 12 columns available, only 8 needed → each column could hold 8 dilutions for one antibiotic-replicate... that gives 4 antibiotics × 2 = 8 columns used, 4 columns spare (sterility controls, sterility + growth controls!). Dilution along rows: transfer with 8-channel? Serial dilution down a column transfers row-to-row within same column — multichannel moves across rows... an 8-channel aligned to a column touches all 8 wells of that column at once — can't do row-to-row transfer with multichannel in that orientation. Serial dilution column-wise (well-to-well down a column) is single-channel work. Multichannel is ideal for column-to-column transfers (across rows), i.e., dilution across the plate horizontally with 12 steps. So my original layout is right for the 8-channel.

So final: rows = antibiotic replicates, dilution across columns 1–11, col 12 = growth control. Seeding issue as discussed.

Let me also consider: maybe do seeding with the multichannel using all 8 tips from trough — but fill each reservoir channel only in... no.

Alternatively: put 2× antibiotic stocks in the reservoir, and use 4 separate aspirate/dispense cycles where each cycle uses fresh tips and aspirates only enough in the top... all 8 tips aspirate — you'd dispense Abx1 to all 8 wells of column 1? That's wrong (different antibiotics per row).

Unless — layout change: 2 antibiotics per plate half? No.

OK, writing the answer now. Structure:

1. Assay design summary: plate map, concentrations, volumes (2× scheme, final 100 µL/well).
2. Deck layout.
3. Reservoir map (12-channel): slot assignments: 1=media, 2=Abx1, 3=Abx2, 4=Abx3, 5=Abx4, 6=bacteria, 12=waste.
4. Protocol steps with logic.
5. Python protocol code (Opentrons API v2) — should I include full code? That's very helpful. Include a solid protocol script. Handle seeding: I'll code it with a single-channel pipette option, or code the multichannel trick? I'll code using single-channel for seeding and note the requirement. Or use the multichannel for seeding by aspirating from reservoir into... hmm.

Actually for code simplicity and correctness, I can code seeding with the 8-channel pipette in this way: for each antibiotic, use `pipette.pick_up_tip()` then... no.

Let me just code with two pipettes: P300-Single (GEN1 or GEN2) on right, P300-Multi 8 (GEN2) on left. User asked about 8-channel; adding a single is a minor, standard addition; I'll note manual alternative. Actually many OT-2s come with both. I'll code it that way and explain.

Wait — actually there's an even cleaner idea for seeding with ONLY the 8-channel: place the four 2× antibiotic stocks into column 1 positions of a SPARE 96-well plate... or even better: put stocks into a reservoir... no.

Hmm, what about this: put the 4 antibiotic 2× stocks in a 2 mL deep-well plate at A1, A2, A3, A4? Then 8-channel picks 8 tips from the tip rack... The problem remains picking single liquid with multichannel. The tip-positioning trick: with 8 tips mounted, command pipette to move to well B1 of the stock plate (row B is one position up from A) so the bottom tip is over A1. `pipette.aspirate(210, stock_plate['A1'].bottom(2))` — the API would place... with a multichannel and a well location, the API moves the pipette so that... For multichannel, passing a single well location: the pipette is positioned so the LAST channel (bottom-most tip? actually channel alignment: multichannel aligns its topmost tip? I believe when you give a single well to a multichannel, it positions the back (top) channel over the well, so the remaining 7 tips are one row down (over B–H). So `aspirate(vol, plate['A1'])` with 8-channel = liquid enters tip 1, other tips over B1...H1 empty wells (if plate). That works for a plate but NOT a trough reservoir. So: antibiotics in a deep-well plate at row A of 4 columns → 8-channel aspirates with top tip into A1 stock, dispenses to... dispense target A1 and B1 of assay plate: move so top tip over assay A1, dispense half, move down... but the API with multichannel at single well similarly offsets. You can dispense by targeting plate['A1'] then plate['B1'] — top tip over A1 then over B1? Positioning: for well B1, top tip over B1, tip1 now over C1 (empty, fine). So each dispense uses tip 1. Yes this works! Uses 8 tips, all carried antibiotics individually if we use successive tips: tip k for antibiotic k, dispensing to rows 2k-1, 2k.

But explaining this in code is doable: for antibiotic i (0–3), use position offset. Implementation:

for i, (abx_source, target_wells) in enumerate(...):
    pipette.aspirate(vol, sources[i]) → hmm but need tip i over source. With top-tip alignment, to use tip i, target the source well shifted i rows down. Deep-well plate only has... source in well A(i+1)... rows A–H exist. Put stocks in column 1 rows A–D? Then to use tip 2 (i=1), target 'B1' with top tip → tip 2 over A1? Wait: top tip over B1 means tip2 over... tips spaced 9mm = one row: tip1 is one row BELOW top tip? Geometry: 8-channel tips point down, arranged vertically; top tip is highest (row A position). If pipette positioned so top tip at row B, then tip 2 at row A? No — tips below top: tip 2 is lower = row C? Rows increase downward on plate. The pipette's tips: the topmost tip and 7 below it. If topmost tip over row A, tip 2 over row B, ..., tip 8 over row H. To use tip k over row A well, position pipette with tip k over A → top tip over row above A — off plate! Can't position above row A (well coordinate of "row -1" doesn't exist, but we can pass a modified location with offset). You CAN do `stock_well.top(z)` plus manual offset, or use `plate.rows()[...][...]`... Actually simplest: put stocks in rows E–H (say H1? tip8 is bottom = lowest row). If stocks in H1–H4? Hmm: put stock i in row (H - i)? Let me think: want tip (i+1) over stock well. Tip (i+1) from top. Position pipette so top tip is i rows above the stock row. If stock in row H (last), then to use tip 1, top tip at row H → tip1... tip 1 IS the top tip? Numbering: topmost tip = tip 1. So tip1 over row H means top tip over H, tips 2–8 below plate — fine (they're off-plate, might crash into plate frame? Tips 7 rows below = beyond plate bottom edge; the pipette moves down over the well; other tips extend below the plate deck level? Row H is the last row; tips 2–8 would be beyond the plate's south edge, hanging over empty deck — OK if no labware there. Deck slot below slot... if plate in slot 2, south neighbor is slot 5/6 area — must be clear or tips hit. Getting too complicated.

Simplest coding: use `pipette.aspirate(volume, well.top(-1))` offsets? The API actually handles multichannel at single wells by aligning the FIRST (top) channel. Known community approach: `pipette.aspirate` with location = a well + `pipette._generate_axis...` no.

Honestly, for the answer, I'll recommend: seeds dispensed by single-channel pipette if available; otherwise manual preload of column 1 with multichannel... or the simplest robust robot-only solution: put 2× stocks in the reservoir; add 100 µL of each antibiotic... 

WAIT. New idea — reverse the seeding: instead of seeding column 1 with pure stocks and diluting rightward with media, seed ALL columns with... no.

Another practical solution used in real MIC protocols: dilute in the reservoir? No.

Another: What if each antibiotic's 2 rows are seeded using the 8-channel with tips picked such that only... okay I've exhausted this; go with single-channel pipette recommendation + manual fallback. Many users doing MIC have both mounts anyway.

Actually, hmm, one more clean option: 2 antibiotics across rows isn't required — what about assigning each antibiotic replicate to a row but seeding via dispensing antibiotic along the row with the multichannel as it's dispensing media? Like: first dispense antibiotic 1 (100 µL) into... you'd dispense to entire column 1 all 8 wells only with same liquid.

FINAL: single-channel pipette for seeding, or manual. Good.

Also mixing considerations: mix 3–5x at each dilution step, blowout, change tips between columns, air gap to reduce carryover. Bacteria addition: 50 µL to all wells, mix after? Gentle. Also incubation note, McFarland standardization, plate reader.

Concentration range example: choose top concentration based on breakpoints, e.g., col 1 = 2× target... give example table: if stock (2×) = 512 µg/mL in col 1 → final concentrations col 1–11: 256, 128, 64, 32, 16, 8, 4, 2, 1, 0.5, 0.25 µg/mL; col 12 = 0 (growth control). Final volume 100 µL/well.

Let me now write the protocol code (API v2, OT-2):

```python
from opentrons import protocol_api
metadata = {...}
requirements = {"apiLevel": "2.16"}

def run(protocol):
    # labware
    tips = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    tips2 = protocol.load_labware('opentrons_96_tiprack_300ul', 4)  # second rack recommended
    plate = protocol.load_labware('...96 well plate...', 2)  # e.g. 'corning_96_wellplate_360ul_flat'
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 3)
    m300 = protocol.load_instrument('p300_multi_gen2', 'left', tip_racks=[tips])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tips2])

    media = reservoir['A1']
    abx = { 'Abx1': reservoir['A2'], ... }  # wait 12-reservoir naming: A1..A12 (single row)
```

12-channel reservoir well names: A1–A12.

Reservoir map:
- A1: Media (large volume needed: 11 cols × 8 wells × 50 µL = 4.4 mL + dead volume; use big slot — the usascientific 22mL channels fine)
- A2: Abx1 (2× stock), A3: Abx2, A4: Abx3, A5: Abx4 (each need ≥ ~0.3 mL + tip submersion; 22 mL channels fine)
- A6: Bacterial inoculum (12 cols × 8 × 50 = 4.8 mL)
- A12: Waste (for discarding from col 11; also blowout)

Steps:
1. Media: m300.pick_up_tip(); distribute 50 µL media to cols 2–12 (reuse tips, distribute with disposal). Then drop tips? Could reuse for... keep tips? drop.
   Actually distributing to 88 wells × 50 µL = 4400 µL; distribute in chunks (aspirate 300 µL, dispense 6 wells...). Code: use `m300.distribute(50, media, [well for col in plate.columns()[1:] for well in col])`. Distribute handles it.
2. Antibiotics: p300 single: for each antibiotic, aspirate 2× stock 100 µL ×2 (200 µL total, aspirate 210?), dispense 100 to each of the two target wells in column 1. Use new tips each antibiotic. Add touch tip / blow out.
3. Serial dilution: for i in range(10): m300 pick up tips (fresh), transfer 50 from col i to col i+1 with mix before (mix 3× 40 µL in source), new tips each transfer. After last, remove 50 µL from col 11 to waste. Actually structure: for each of columns 1→2 ... 10→11: transfer 50, mix. Then from col 11, transfer 50 to waste.
4. Bacteria: m300 pick fresh tips, distribute 50 µL bacteria to ALL 96 wells. Mix? dispense into each well — distribute will dispense into liquid; can add mix. To avoid aerosol, mix gently 2×.
5. Tips handling: total multichannel pickups: media 1 + dilution 10 + waste removal 1 + bacteria 1 = 13 pickups × 8 tips = 104 tips > 96! Need second tip rack. So two racks of 300 µL: rack1 slots... Let's say tip racks in slots 1 and 4 (m300 tip_racks=[tips1, tips2]... wait p300 single also needs tips — single can pick from same rack columns? Single channel picks from well A1 etc. Sharing rack with multichannel: multichannel picks whole columns; single picks individual tips — could conflict. Cleanest: give p300 its own... or have p300 use tips2 as well — Opentrons tracks usage; single uses individual tips from wherever available; multichannel needs full columns. Could co-exist if single picks from a column multichannel won't use... risky. Better: put 4 antibiotic additions = 4 single tips from a dedicated rack or... Actually simpler: have m300 do antibiotics too?? No.

Alternative to save tips: reuse the media tips for the... no, contamination. Hmm: Could reuse tips across the dilution transfers? No — cross-antibiotic contamination (row A → row B carryover). Actually wait — how bad? Tip used for col1→2 transfer touches all 8 rows including Abx1 wells and Abx4 wells. Reusing for col2→3: carryover of Abx1 into Abx4's column-2 wells. Concentrations tiny but MIC is sensitive. Recommend fresh tips.

So tip count: 13 multichannel pickups = 104 tips → two 300 µL racks. Plus single channel 4 tips. Arrange: slots 1 & 4? No wait — reservoir in 3, plate in 2? Let me lay out deck:

- Slot 1: tiprack 300 (multi)
- Slot 2: 96-well plate — hmm, actually many prefer plate in middle/slot 6... With multichannel accessing plate columns, plate position doesn't matter much. But single-channel reach: right mount pipette can't reach slot 1 area? Right mount CAN reach slots 1,2,3? On OT-2, right mount cannot reach... actually the right mount cannot reach the leftmost columns of slots... I recall right-mount pipettes can't reach slot 1 (and part of 4, 7). Left mount can't reach slots... left mount can't reach slot 12? Common guidance: right pipette can't reach far-left of slots 1,4,7; left can't reach far right of 12,9? Something like that. Safe deck layout:
  - Slot 1: 300 µL tiprack #1 (left mount multichannel will use; single right mount may not fully reach slot 1 → put single's tips elsewhere)
  - Slot 2: nothing/reservoir? 
  Let me pick:
  - Slot 2: 96-well assay plate (center-ish)
  - Slot 3: 12-channel reservoir
  - Slot 1: tiprack (shared? risky) 
  Plan: 
  - Slot 1: 300 µL tiprack — multichannel
  - Slot 4: 300 µL tiprack #2 — multichannel overflow AND single-channel picks from here (single on right can reach slot 4; multichannel picks full columns from here too, but single might fragment columns — Opentrons tip tracking handles it: multichannel will skip fragmented columns? It would fail if no full column available. Risk: single uses 4 tips within a column, then multichannel tries that column. The tip tracker: multichannel pick_up_tip picks the next available full column — it uses the same tip tracker; if single consumed A1–D1, multichannel can't use column 1 and moves on? I believe multichannel auto tip picking picks the first column where ALL 8 tips are available, skipping partially used. I think it errors... not 100% sure. Safer: single uses rack in slot 5, multi uses slots 1 and 4.)

  Final deck:
  - Slot 1: 300 µL tiprack (multi, rack A)
  - Slot 4: 300 µL tiprack (multi, rack B)
  - Slot 5: 300 µL tiprack (single) — or actually we can reduce: single only needs 4 tips; put its rack in slot 5 or 6? Hmm, deck slots: 1–11 (3,6,9? no—OT-2 deck: slots 1-11 where 3,6,9 are... no that's the larger deck. OT-2 has slots 1–11: 1,2,3 top row... Actually OT-2: slots 1–3 top? No: OT-2 deck layout: 3 cols × 4 rows minus center = slots 1,2,3 (back row... ) Standard OT-2 slots: 1 (top-left), 2 (top-center), 3 (top-right), 4 (mid-left), 5?? Hmm the OT-2 has slots 1,2,3 across the back; 4,5,6 middle row (5 is center); 7,8,9 front row; plus 10,11 special (10 = right of slot 9? slots 10 and 11 are the two small... no). OT-2: 11 slots: back row 1-2-3, middle 4-5-6, front 7-8-9, and 10, 11 which sit... 10 and 11 are the left/right of the... they're the small slots beside slot 3? I recall slots 10, 11 exist below... Slot 10 is to the right of 9? No: OT-2 deck: slots 10 and 11 are the positions flanking... Actually they're located in the middle row's outer... Let me recall: the OT-2 deck has 11 slots arranged 3 wide × 3 tall (1-9) plus 2 extra (10, 11) — 10 is at the far right of the top? Honestly: 10 and 11 are the two positions in the... In the standard Opentrons deck map, slot 10 is to the right of slot 9? I believe slots 10 & 11 are on the left and right of the middle row: no...

  The OT-2 deck: Row A (back): slots 1, 2, 3. Row B (middle): 4, 5, 6... no wait, there are only 3 rows visible + the special slots. The actual map: it's 3 columns × 4 rows where middle-column slots are split: slots 1,2,3 top row; 4,5,6 second row? Ugh. Standard OT-2: 
  ```
  1  2  3
  4  5  6
  7  8  9
    10 11
  ```
  where 10 and 11 are the lower-middle slots (small, flanking below? no—) Actually: OT-2 deck is 3×4 grid: left column: 1,4,7,10; middle column: 2,5(=large center),8,11? The correct answer: OT-2 deck slots: 
  - 1, 2, 3 across the BACK
  - 4, 5, 6 across the middle... no, the middle has 4 (left), 5 (center? no—5 doesn't exist as separate)... 

  OK truth: OT-2 has slots 1–11. Common configs: plate in slot 2, tipracks 1 and 3, etc. Slot 5 is center. The grid: 3 columns × 3 rows for slots 1–9 (1 top-left, 3 top-right, 7 bottom-left, 9 bottom-right). Slots 10 and 11 are located: 10 below 1? They are the small slots at bottom-left (10) and bottom-right (11)? I believe slot 10 is to the left of 7?? Honestly, standard doc: slots 10 and 11 are beneath slots... they're "the two slots at the bottom-center": positioned below 8: no. 

  I recall: OT-2 deck = 4 rows: row1: 1,2,3; row2: 4,5,6? No — OT-2 only has 3 rows of full slots? The OT-2 deck is smaller than Flex. Map (from Opentrons docs): 
  ```
  1   2   3
  4   5   6
  7   8   9
  ```
  with slots 10 and 11... In opentrons sim error messages you see "slot 10" and "slot 11" — they are the small slots in the middle column, i.e., 10 is between 7 and 8? The docs: "Slots 10 and 11 are the two small slots on the left and right of the... " 

  From memory of the Opentrons deck map image: OT-2 deck: back row: 1 2 3; middle row: 4 5 6 is WRONG because there are only 3 rows + 2 extra. Actually correct: it's:
  ```
   1  2  3
   4     6    <- middle row has 4 (left), 6 (right)? no...
  ```
  I now recall clearly: OT-2 slots: 1,2,3 (back row); 4 (middle-left), 5 (middle-center), 6 (middle-right); 7,8,9 (front row); 10 (below 5? no—10 and 11 are the small slots in the front... 

  Opentrons deck: slot 10 is located between slots 9 and 11 at the bottom? The official map shows 11 positions: back 1-2-3, middle-left 4, center 5? NO. Let me settle: The widely cited OT-2 deck layout:
  - Back row: 1 (left), 2 (center), 3 (right)
  - Middle row: 4 (left), 5 (center), 6 (right)
  - Front row: 7 (left), 8 (center), 9 (right)
  - Slots 10 and 11: below/front? They are the left and right slots in the... 10 is to the LEFT of 7?? 

  Real answer (I'm fairly confident now): OT-2 deck has 11 slots; slots 10 and 11 are the two small slots located in the middle row's far sides? Hmm no — I've definitely seen: "slot 10" is a small slot between slots 1/4 and 2/5? 

  Actually yes! I remember: the OT-2 deck's middle row is split: on the left there are two half-height slots (4 and 10) and on the right two half-height slots (11 and 6), with the large center slot 5. So middle row: 4, 10 (stacked) on left; 5 center; 11, 6 (stacked) on right. Slots 10 and 11 are small (half-length), suitable for tipracks (50 µL) or small modules. Yes — that's right: 4 is above 10, and 11 is above 6. So middle row left-to-right: 4 (upper-left-half), 10 (lower-left-half), 5 (center), 11 (upper-right-half), 6 (lower-right-half). Hmm, or 10 above 4? I think 4 is the top one and 10 below it; 11 top-right small, 6 bottom-right... Actually I recall slot 11 is above slot 6? and slot 10 is above slot... whatever — minor detail. To avoid errors, I'll assign: slots 1, 2, 3 for big items? But 10/11 too small for full tiprack (they fit 96-tiprack? They're half-size... they can hold a 96-tiprack? No—too small; they fit the opentrons_96_tiprack uses full slot... Hmm, actually I recall tip racks CAN go in 10/11? The small slots fit... no.)

  To be safe, I'll use only slots 1–9 in my layout and note positions can be adjusted:
  - Slot 1: tiprack 300 µL #1 (left pipette / multichannel)
  - Slot 2: 96-well plate... hmm wait, better ergonomics: plate in slot 2 or 3? Doesn't matter much. Let me do:
  - Slot 1: 300 µL tiprack #1
  - Slot 2: 12-channel reservoir (back center — good, user loads from front? front is better for user access. Reservoir at slot 8 (front center) is nice for loading.)
  - Slot 3: 300 µL tiprack #2
  - Slot 5?? 5 is center — could hold plate? Plate in slot 6? 

  Practical: 
  - Slot 2: assay plate (back-center) — robot reaches fine; user can access from back? OT-2 access is from front. Put plate in slot 6 (mid-right) or 8 (front-center) for visibility.
  
  Simple, common layout:
  - Slot 1: tiprack 300 µL (multi #1)
  - Slot 2: 96-well plate... but also need reservoir + 2nd tiprack + single's tips.
  
  Total items: 1 reservoir, 1 plate, 2 multichannel tipracks, 1 single tiprack (or share). Could share: single channel uses only 4 tips; let it pick from rack #2 in slot 3 — right mount CAN reach slot 3? Right mount reaches slots... right mount pipette can't reach slot 1 region; slot 3 should be reachable (right side). And left multichannel reaches all? Left mount can't reach far right of slot 9? Left mount CAN reach slot 3? I think left mount reaches everything except maybe far edge of slots 3/9 right column? Historically: "left pipette cannot reach slot 9?" Hmm. The known limitation: right-mount pipettes cannot access the leftmost column of slot 1, 4, 7? and left-mount cannot access rightmost part of 3, 6, 9? I recall the right GEN2 single can't reach wells in the far-left of slots 1,4,7; left mount can't reach far-right of slots 3,6,9. With a 12-well reservoir in slot 3 and left mount reaching A12 (rightmost)... could be an issue. Keep reservoir in middle-left/middle: slot 4? but 4's far-left unreachable by right single (doesn't need reservoir though — single only touches plate col 1 (slot ?) and antibiotic reservoir slots).

  Final deck plan (safe):
  - Slot 1: 300 µL tiprack #1 (multichannel) — left mount reaches fine.
  - Slot 2: 300 µL tiprack #2 (multichannel overflow)
  - Slot 3: nothing? Or put plate in 3? left mount reaching plate col 12 (rightmost column of slot 3) — multichannel needs full access to plate columns 1–12! If plate in slot 3, left mount might not reach column 12. So plate should be in slot 2, 5, or 8 (center column) or left column with left mount. Put plate in slot 2? But then tipracks... 

  Layout:
  - Slot 1: tiprack 300 µL #1 (multi)
  - Slot 2: 96-well assay plate — left mount reaches all columns of slot 2? Yes, slot 2 center-column fully reachable by both mounts (except maybe extremes? center column slots are safe).
  - Slot 3: 12-reservoir (center? no 3 is right column top) — left mount may struggle with A12 (rightmost well of reservoir in slot 3). Move reservoir to slot 5? Slot 5 center — but slot 5 is the large center slot; reservoir fits. Hmm, but then tiprack #2 where? 
  - Slot 4: tiprack 300 #2 (left mount reaches slot 4 fine? slot 4 is left-middle — yes).
  - Slot 5: reservoir? Or reservoir slot 3 with risk. Alternative: reservoir in slot 5 (center) — fully reachable by both mounts. Then plate slot 2? Wait plate also center-ish; plate in 2, reservoir 5? Fine.
  - Slot 6: single-channel tiprack? Right mount reaches slot 6 (right-middle) — but left mount may not need it. Single only needs to reach: reservoir (slot 5) and plate col 1 (slot 2) — both center column. Right mount fine.
  
  But wait — I listed 4 tipracks total? 2 multichannel racks (104 tips) + 1 single rack (only 4 tips used — could use a 96 rack, wasteful but fine, or share). Alternatively reduce multichannel tip usage to 96 to fit one rack:
  Tip-saving: the waste-removal step (remove 50 µL from col 11 to waste) could reuse the tips from the last dilution transfer (tips touched col 10→11, removing from col 11 with same tips — no new contamination, same antibiotics). That saves 1 pickup → 12 pickups = 96 tips exactly. And bacteria step needs tips too! 13th... reuse dilution tips for bacteria? Tips carry antibiotics; bacteria goes INTO wells — carryover of antibiotic traces into growth control well col 12? Tiny but MIC-sensitive... The col-12 growth control getting traces of antibiotics from tips — could suppress growth slightly. Use fresh tips: need 13 pickups. 104 > 96. So two racks needed. Alternatively, single-channel p300 could distribute bacteria? 96 wells single channel = slow but OK (96 dispenses). Nah.

  Alternative: drop the multichannel media-distribute tips reuse... media needs 1 pickup. Count minimal: media 1, dilution 10, bacteria 1 = 12 pickups with reuse of last dilution tips for waste removal = 96 tips exactly fits one rack! And antibiotic seeding via SINGLE channel from separate rack (4 tips). 

  That's elegant: one 300 µL rack for multichannel (12 column pickups × 8 = 96), and single channel... can share the same rack? Single would break columns. If single uses 4 tips from, say, column 12 of the same rack before multichannel runs — then multichannel auto-pick would skip? The multichannel tip tracker picks the first available FULL column. If single took 4 tips from column 1's A–D, multichannel would... I believe it errors only if no full columns remain; it searches for full columns? Actually with tip_racks auto assignment, multichannel picks the next column where all 8 tips unused; partial columns are skipped? I'm not 100% sure it skips gracefully. To be safe in code: assign single channel's starting tip explicitly: p300.starting_tip = tips['E1']? then single uses E1–H1? still partial column. Hmm, if single picks E1,F1,G1,H1 (lower half of column 1), multichannel picking column 1 would fail since 4 used. Unless multichannel skips. 

  Safer: two racks anyway, or have the single channel pick tips from a separate rack. I'll just include two 300 µL racks (slot 1 and slot 4) — cheap and safe: multi uses both, single uses rack 2... same fragmentation risk. OK: assign explicitly: m300.tip_racks=[rack1] only (96 tips = exactly 12 pickups ✓), p300.tip_racks=[rack2], start p300 at rack2['A1']. Clean. Deck:

  - Slot 1: 300 µL tiprack #1 (multichannel)
  - Slot 2: 96-well assay plate
  - Slot 3: (empty or... nothing) — hmm, could hold nothing. Actually reservoir: 
  - Slot 4: 300 µL tiprack #2 (single channel) — right mount reaching slot 4: slot 4 is middle-left; right mount CANNOT reach left column slots fully! Right pipette can't reach slot 1, and far-left of 4, 7. A tiprack in slot 4 — right single needs to pick tips at H1 (bottom-left well) — unreachable? The rule: right mount can't reach the leftmost ~1 well column of slots 1,4,7? For slot 4, all wells might be reachable? The known spec: right mount cannot reach "left most column of slot 1" and I think slot 4/7 are fine? Hmm, the official statement: right pipette can't reach left edge of slots 1, 4, 7? I've seen "cannot access the leftmost column of slot 1 and partially slot 4, 7". To be safe: put single's rack in slot 5 (center) or 6 (right). Slot 6: right-middle — reachable by right mount ✓.
  - Slot 5: 12-channel reservoir? But wait — bacteria slot must be reached by multichannel (left mount) — slot 5 center: left mount reaches center ✓.

  Hmm but actually maybe put reservoir slot 5? Many protocols put reservoir in 5? Sure. But then where's waste? In the reservoir A12.

  Deck final:
  - Slot 1: 300 µL tiprack (multi, 96 tips)
  - Slot 2: 96-well assay plate
  - Slot 5: 12-channel reservoir? Hmm — actually I realize plate in slot 2 with multichannel reaching column 12 of plate (rightmost column of slot 2): center column slots fully reachable ✓.
  - Slot 6: 300 µL tiprack #2 (single channel)
  Wait, but can LEFT mount reach slot 6 (right column)?? Left mount pipettes cannot reach... left mount CAN reach right column slots? The limitation for left mount: cannot reach slot 11/6? I recall: "left mount cannot access right-most column of slots 3, 6, 9"? If multichannel doesn't need slot 6 (only single does) — fine. Multichannel needs: slot 1 rack, slot 2 plate, slot 5 reservoir — all left/center ✓. Single needs: slot 5 reservoir (center ✓), slot 2 plate col 1 (center ✓), slot 6 rack (right ✓ for right mount). 

  This works! Deck:
  - Slot 1: 300 µL tiprack #1 — 8-channel
  - Slot 2: 96-well plate
  - Slot 5: 12-channel reservoir (center)
  - Slot 6: 300 µL tiprack #2 — single channel
  Free: 3, 4, 7, 8, 9 (could put second reservoir for waste or more tips).

  Hmm, one concern: 12-channel reservoir in slot 5 — the "usa scientific 12 reservoir 22 ml" is long (like trough orientation?) fits standard slot ✓.

  Reservoir mapping (A1–A12):
  - A1: Media (MHB-II), ~5 mL + dead volume
  - A2: Abx 1 (2× top concentration)
  - A3: Abx 2 (2×)
  - A4: Abx 3 (2×)
  - A5: Abx 4 (2×)
  - A6: Bacterial inoculum (2× target density, ~5–6 mL)
  - A12: Waste (or empty trough; can also put sterile water for rinsing)
  
  Note: each antibiotic needs only ~200 µL but pipette must reach bottom of 22 mL trough — dead volume! In a 22 mL channel, 200 µL is a shallow layer; multichannel/single can aspirate from bottom(1)? Single channel can reach `reservoir['A2'].bottom(1)` — fine with ~250+ µL. Actually single can aspirate down to near bottom with ~300 µL present. Recommend loading ≥1 mL each to be safe. Alternatively use a smaller reservoir for antibiotics... note it.

  Wait, actually there's a subtlety: for seeding I said aspirate 2× stock... single channel aspirates 200 µL (100 per well × 2 wells) plus could do 210 with air gap. Aspirate 210, dispense 100+100, blow out. Fine.

  Volumes recap (2× scheme, final 100 µL/well):
  - Media into columns 2–12: 50 µL/well (88 wells = 4.4 mL + dead volume; load ≥6 mL... distribute uses disposal volume too. Say load 8–10 mL? For 22 mL channel fine.)
  - Antibiotic 2× stock into column 1: 100 µL/well (8 wells: 2 per antibiotic). Load ≥0.5–1 mL each.
  - Serial dilution: 50 µL column to column, 1–11, discard final 50 µL from col 11 (into waste A12).
  - Bacteria: 50 µL/well to all 96 wells (4.8 mL + disposal, load ≥7 mL).
  
  Final per well: 100 µL. Col 1 concentration = stock/2? Let's verify: col 1 = 100 µL of 2× stock at concentration C. After transferring 50 to col 2, col 1 has 50 µL at C. Col 2 = 50 media + 50 from col1 = 100 µL at C/2, then transfer 50 out → 50 µL at C/2. Etc. Col 11 = 50 µL at C/1024. Col 12 = 50 µL media (0 antibiotic). Then 50 µL bacteria (at 2× inoculum) added everywhere → final 100 µL, col 1 = C/2 final, col k = C/2^k... col 1 final = C/2, col 11 = C/2048? Wait col 11 at C/2^10 = C/1024 (2× concentration), final after bacteria = C/2048. Hmm: col1 2×conc = C, final = C/2. So final range: C/2 down to C/2048, i.e., 11 two-fold dilutions: col1=C/2, col2=C/4,... col11=C/2048. Yes: 11 concentrations, factor 2^10 = 1024 range. If you want final top concentration 256 µg/mL, make stock C = 512 µg/mL (the "2×" here means 2× relative to final col-1 concentration). So: prepare antibiotic stock at 2× the desired highest FINAL concentration. Good — I'll state: desired top final conc = X → load X×2 into reservoir (well, load stock of 2X).

  Wait check col 12 growth control: media 50 + bacteria 50, no antibiotic ✓.

  Optionally include sterility control: could dedicate... all 96 wells used. Could use a second plate or note that a media-only blank column would require a 9th row. Just mention.

  Mixing in serial dilution: at each transfer, mix destination 3× 40 µL before moving on. Also mix before aspirating from source (the previous mix did that). Order: transfer col i → i+1: aspirate 50 from col i (already mixed from previous step or seeding), dispense into col i+1, mix 3×, then move on. Also blow_out? Careful: blow out extra volume changes concentration — use careful aspirate/dispense with touch tip. Standard: transfer 50 µL with mix_after, new tips each column.

  Bacteria addition: distribute 50 µL to all 96 wells; optionally mix_after 2× gently. Also important: bacteria suspension mixing — reservoir should be mixed periodically? Keep simple; note it.

  Also mention inoculum standardization: 0.5 McFarland ≈ 1–2×10^8 CFU/mL, dilute to 2×10^6 in reservoir? CLSI: final inoculum 5×10^5 CFU/mL. With 2× scheme: bacteria in reservoir at 1×10^6 CFU/mL → final 5×10^5. Note.

  Also incubation: 35±2°C, 16–20h, ambient air, MIC = lowest conc with no visible growth.

  Now write the code. Keep it clean:

```python
metadata = {
    'protocolName': 'MIC 2-fold broth microdilution - 4 antibiotics x 2 reps',
    'author': '...',
    'apiLevel': '2.13'
}

def run(protocol):
    # --- labware ---
    tiprack_multi = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    tiprack_single = protocol.load_labware('opentrons_96_tiprack_300ul', 6)
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 5)

    m300 = protocol.load_instrument('p300_multi_gen2', 'left', tip_racks=[tiprack_multi])
    p300 = protocol.load_instrument('p300_single_gen2', 'right', tip_racks=[tiprack_single])

    # reservoir slots
    media = reservoir['A1']
    abx_stocks = [reservoir['A2'], reservoir['A3'], reservoir['A4'], reservoir['A5']]
    bacteria = reservoir['A6']
    waste = reservoir['A12']

    # plate map: rows A/B = Abx1, C/D = Abx2, E/F = Abx3, G/H = Abx4
    abx_rows = [
        ['A', 'B'],  # antibiotic 1
        ['C', 'D'],  # antibiotic 2
        ['E', 'F'],  # antibiotic 3
        ['G', 'H'],  # antibiotic 4
    ]

    VOL_MEDIA = 50
    VOL_SEED = 100
    VOL_TRANSFER = 50
    VOL_BACTERIA = 50

    # 1) media into columns 2-12
    m300.pick_up_tip()
    dest = [w for col in plate.columns()[1:] for w in col]
    m300.distribute(VOL_MEDIA, media.bottom(2), dest, disposal_volume=20, blow_out=True?...)
```

Hmm, distribute from a reservoir with multichannel — fine. disposal volume 20, new_tip each? Since we manually picked tips, distribute with... distribute auto-uses tips? If tips already attached, distribute uses them. disposal_volume default 20%... set 20.

Actually careful: distribute for 88 wells × 50 = 4400 µL; distribute splits into as few passes as possible (300 µL max per aspirate = 6 dispenses... 50×6=300 exactly, no room for disposal — with disposal 20, aspirate 320? max 300. So distribute: aspirate 300, dispense 5 wells (250), disposal 20, blow out? distribute handles. It'll do many passes with same tip ✓.

Then drop tips, return.

2) Seed column 1:
```python
    for i, (stock, rows) in enumerate(zip(abx_stocks, abx_rows)):
        p300.pick_up_tip()
        p300.aspirate(VOL_SEED*2, stock.bottom(2))
        for r in rows:
            p300.dispense(VOL_SEED, plate[r+'1'].bottom(5))
        p300.blow_out()  # hmm blow out remaining ~0 after 2x100 with aspirate 200 exact... aspirate 210, dispense 100, dispense 100, blow_out remaining 10 into waste
        p300.drop_tip()
```
Better: aspirate 210, dispense 100 each well, then blow_out into waste? blow_out() blows into last dispense location — 10 µL extra into second well! That changes its concentration (well gets 110 µL instead of 100). Hmm: with 110 in B1 vs 100, subsequent serial dilution transfers 50 out leaving 60 vs 50 — concentration differs slightly (un-mixes the 2-fold series: B1 would be at C×(100/110)... slightly higher. Minor error but let's avoid: aspirate exactly 200, dispense 100, 100, then blow_out pushes air only (no residual). Accuracy: single dispense of 100 from 200 aspirate is fine. Or aspirate 205 with air gap... Keep simple: aspirate 200, dispense 100 twice, blow_out (should be empty, just clears tip), touch tip optional. Actually blow_out with nothing left is harmless ✓.

3) Serial dilution:
```python
    for i in range(10):
        src = plate.columns()[i]
        dest = plate.columns()[i+1]
        m300.pick_up_tip()
        m300.transfer(VOL_TRANSFER, src, dest, mix_after=(3, 40), new_tip='never', blow_out=False?)
        m300.drop_tip()
    # wait - transfer with new_tip='never' and pre-picked tips ✓. blow_out? default transfer blow_out False for... transfer default blow_out? default is False? Actually default blow_out=False? I think default is blow_out False for transfer... The default for transfer is `blow_out=False`. Hmm, I believe default is False. Set explicitly.
```
Careful with volumes: transfer 50 from col to col — residual droplet changes conc slightly; standard protocols accept; add touch_tip on dest? m300 transfer with touch_tip=True touches sides of all 8 dest wells ✓ nice.

Then remove 50 µL from col 11 → waste. Reuse the last tips? After loop tips dropped. Just do another pickup (13 total > 96!). Recount pickups: media 1 + dilution 10 = 11 → waste removal 12 → bacteria 13 = 104. Over 96. Fix: in the dilution loop, keep the last iteration's tips for waste removal (don't drop inside loop; restructure):

```python
    for i in range(10):
        m300.pick_up_tip()
        m300.aspirate(VOL_TRANSFER, plate.columns()[i]... 
```
Write explicit: after final transfer (i=9, col10→11), with tips still on: aspirate 50 from col 11 (all 8 wells), dispense into waste. Then drop tips.

So:
```python
    for i in range(10):
        m300.pick_up_tip()
        m300.transfer(VOL_TRANSFER, plate.columns()[i], plate.columns()[i+1],
                      mix_after=(3, 40), new_tip='never', touch_tip=True)
        if i < 9:
            m300.drop_tip()
        else:
            # remove excess from column 11 into waste, reusing these tips
            m300.aspirate(VOL_TRANSFER, plate.columns()[10])
            m300.dispense(VOL_TRANSFER, waste)
            m300.drop_tip()
```
Hmm aspirate from a column (list of wells) with multichannel — passing a column (list) works? `plate.columns()[10]` returns list of wells; better `plate.rows()` ... for multichannel, pass the column list or use plate['A11']...? With a multichannel, giving a single well (e.g., plate['A11']) makes all 8 tips align to that column ✓. Use plate['A11']? That aligns tips over column 11 rows A–H? When a multichannel is given well A11 (top row), it aligns top tip to A11 → all 8 tips over A11–H11 ✓. Actually the convention: multichannel + single well = pipette positions over the column starting at that well. Yes.

So use `m300.aspirate(50, plate['A11'])`? Hmm, but if I pass plate.columns()[10] list — also fine. I'll use plate['A11'] style but safer to pass the column list. Both okay; I'll use column list.

Then bacteria:
```python
    m300.pick_up_tip()
    m300.distribute(VOL_BACTERIA, bacteria.bottom(2),
                    [w for col in plate.columns() for w in col],
                    disposal_volume=20)
    m300.mix?  # distribute can't mix; acceptable — final mixing: could do a gentle mix pass after? That would need more tips (pickup #13 = 104). Hmm! Bacteria distribute = 13th pickup. Over budget!
```
Recount: media 1, dilution 10, (waste merged into #10's tips ✓), bacteria 1 → total 12 pickups = 96 tips exactly ✓. 

But wait, does distribute with 96 destination wells work in passes with same tips? 300 µL aspirate / 50 µL dispense = 6 wells per pass + 20 disposal → 300-20=280/50=5.6 → 5 wells per pass... distribute will compute; ~20 passes, same tips ✓.

Mixing after bacteria addition: optional gentle mix — would exceed tips. Skip or note optional second rack. Could instead mix during dispense by distributing with mix? distribute doesn't support mix. Alternative: use `mix_before`? Not for distribute. Note in text: gentle mixing occurs as inoculum is dispensed into 50 µL; acceptable; or add second tiprack and do a 3× mix pass. I'll note it.

Also plate seal/incubation: user handles.

One more check: dilution transfer accuracy — using `transfer` with new_tip='never' after manual pickup ✓. touch_tip on dest column ✓. mix_after=(3,40) but careful: mix 40 µL in wells containing 100 µL — fine.

But hold on: in the dilution loop, mix_after mixes in dest; when moving to next column, we aspirate from previously-mixed well ✓.

Edge: column 1 after seeding has 100 µL; transfer 50 → col 1 keeps 50 ✓. Col 2: 50 media + 50 = 100 ✓.

Bacteria: dispense 50 into all wells → col 1–11: 50 + 50 = 100 ✓; col 12: 50 media + 50 = 100 ✓.

Dead volume / reach: reservoir bottom(2) with 22 mL troughs; advise ≥2 mL loaded in media/bacteria... media needs 4.4 mL + 20 µL disposal × passes. distribute total aspirated = 4400 + overhead ✓ load 6+ mL. Bacteria 4800 + overhead, load 7+ mL. Antibiotics: single channel bottom(2), load ≥500 µL.

Also mention: use columns 11 concentrations C/2 ... to C/2048 — choose stock accordingly; example table.

Include plate map diagram:

```
       Col1    Col2   ...  Col11   Col12
Row A  Abx1    Abx1        Abx1    GC
Row B  Abx1 ...
Row C/D Abx2
Row E/F Abx3
Row G/H Abx4
GC = growth control (no antibiotic)
```

Also mention API level, labware definitions (pick correct labware for their specific plate — instruct to swap the load string; e.g., 'nest_96_wellplate_200ul_flat').

Also runtime notes, calibration, and QC tips: sterility control suggestion, readings at OD600 after incubation, duplicated wells.

Also mention keeping bacteria slot mixed — reservoir agitation not automatic; inoculum should be used promptly, gently resuspended before loading; distribute quickly.

Also: prepare 2× everything rationale.

Also aspirate height for antibiotics: p300.aspirate(..., stock.bottom(2)).

Let me also double check `distribute` on 96-well destinations from reservoir with multichannel: destinations must be organized; passing list of all wells row-major (`for well in plate.wells()`) — distribute groups by column? It might try weird orders for multichannel. Better pass `plate.wells()` flattened column-wise: `plate.columns()` flatten → [A1..H1, A2..H2...]? For a multichannel distribute, destinations as columns list-of-lists works too? Safer: pass list comprehension over columns. distribute will do multipipette grouping when destinations align in columns — I believe distribute with a flat list works with multichannel since consecutive wells in a column are 8-aligned... plate.columns()[i] gives [A..H] ✓ so flatten column-wise gives aligned groups. Use that.

Media distribute: dest columns 2–12 flattened ✓.

One more consideration: `distribute` default `disposal_volume` is 20% of... default is 20? Default disposal_volume = 20 µL? I'll set explicitly.

Also add `protocol.set_rail_lights`? skip.

Also should the bacteria be added AFTER the plate maybe should rest? Fine.

Also mention safety/GMO handling briefly? Light touch.

Write the final answer with:
1. Assay design & plate map (concise)
2. Volumes table
3. Deck & reservoir layout
4. Python protocol (complete)
5. Key notes (inoculum, controls, tips, labware customization, incubation/MIC reading)

Keep code correct-ish. Also note: `mix_after=(3, 40)` inside transfer — yes supported.

Also `touch_tip=True` in transfer touches after dispense... transfer param touch_tip applies after dispense ✓.

For seeding loop code:

```python
    for stock, rows in zip(abx_stocks, abx_rows):
        p300.pick_up_tip()
        p300.aspirate(200, stock.bottom(2))
        for row in rows:
            p300.dispense(100, plate[row + '1'].bottom(5))
            p300.touch_tip(plate[row + '1'])  # hmm touch_tip signature touch_tip(well)
        p300.blow_out(waste)
        p300.drop_tip()
```
blow_out into waste ✓. touch_tip optional.

Wait: plate[row+'1'] — column 1 = plate.columns()[0]; wells 'A1','B1' ✓.

Bacteria distribute: also `blow_out` per? distribute blow_out param True? distribute(blow_out=True)? Not needed since disposal. fine.

Concentration example table:

Stock (reservoir) = 2 × top final conc. If top final = 256 µg/mL → stock 512. Final col conc: 256, 128, ..., 0.125 µg/mL (col 11 = 256/1024 = 0.25? 2^10 = 1024 → col 11 = 256/1024 = 0.25 µg/mL. Let me recompute: col1 = C/2 where C = stock. If top final 256 → stock = 512. col k final = stock/2^k: col1=256, col2=128, col3=64, col4=32, col5=16, col6=8, col7=4, col8=2, col9=1, col10=0.5, col11=0.25, col12=0 ✓.

Alright, write it. Reasonably detailed but organized. Use headers, tables, code block.