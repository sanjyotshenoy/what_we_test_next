// A MOCK trace of one query through the whole pipeline, for the demo page until the agent writes real ones.
// Every number marked mock is illustrative; the IDs (ChEMBL, UniProt, BAO) are real. The shape is the trace
// format in ../README.md: replace this file with the agent's output and the page shows the real run.
// TODO(final): replace this mock with a real trace from the pipeline and set mock: false (the page shows a
// "Mock trace" badge while it is true); fill in the held-out ChEMBL assay ID in validation.held_out.
(window.DEMO_RUNS = window.DEMO_RUNS || []).push({
  id: 'kit-imatinib',
  mock: true,
  query: 'Does imatinib inhibit the KIT kinase, and how potently?',
  model: 'moonshotai/Kimi-K3',

  // 1. what the knowledge base says on its own
  lookup: {
    tool: 'kb.search',
    args: { query: 'imatinib KIT IC50' },
    result: 'No measured activity for imatinib against KIT in the knowledge base.',
    verdict: 'I don’t know',
    note: 'The record that answers it was held out when the KB was built, so the answer is known to us but not to the agent.',
  },

  // 2. tool calls on the graphs, in order
  calls: [
    {
      tool: 'bio_kg.resolve',
      args: { compound: 'imatinib', target: 'KIT' },
      summary: 'Both entities found; the target belongs to a class with protocol templates.',
      rows: [
        ['CHEMBL941', 'Compound', 'imatinib'],
        ['P10721', 'Target', 'KIT (mast/stem cell growth factor receptor)'],
        ['class:tyrosine_kinase', 'TargetClass', 'tyrosine kinase'],
      ],
    },
    {
      tool: 'bio_kg.analogs',
      args: { compound: 'CHEMBL941', target: 'P10721', k: 3 },
      summary: 'Similar compounds with measured activity on this target set the concentration range.',
      columns: ['Compound', 'Similarity', 'IC50 on KIT'],
      rows: [
        ['nilotinib (CHEMBL255863)', '0.71 (mock)', '0.2 µM (mock)'],
        ['dasatinib (CHEMBL1421)', '0.38 (mock)', '0.02 µM (mock)'],
        ['sunitinib (CHEMBL535)', '0.29 (mock)', '0.05 µM (mock)'],
      ],
    },
    {
      tool: 'protocol_kg.templates',
      args: { question_type: 'potency', target_class: 'class:tyrosine_kinase' },
      summary: 'One template fits a potency question on an enzyme: a biochemical dose-response.',
      rows: [
        ['proto:kinase_glo', 'Protocol', 'biochemical kinase inhibition, luminescence readout'],
        ['BAO:0000357', 'Format', 'single protein format'],
        ['BAO:0000190', 'Endpoint', 'IC50'],
      ],
    },
  ],

  // 3. the model's reasoning, as it reported it
  reasoning: [
    'The KB has no measurement for this pair, so this needs an experiment, not an answer.',
    'Potency question + kinase target → the biochemical dose-response template.',
    'Analogs on KIT sit between 0.02 and 0.2 µM (mock), so the series must reach well below 0.1 µM and still show a top plateau: start at 10 µM and dilute 1:3 over 10 points (10 µM down to 0.5 nM).',
    'Controls: DMSO vehicle (0% inhibition) and staurosporine (full inhibition); three replicates.',
  ],

  // 4. the proposal, in the ExperimentProposal shape of wwtn/schema.py
  proposal: {
    answerable_from_kb: false,
    experiment: {
      assay_type: 'biochemical kinase inhibition (dose-response)',
      readout: 'luminescence (ADP formed)',
      system: 'recombinant KIT kinase domain',
      top_concentration_uM: 10,
      dilution_factor: 3,
      n_points: 10,
      replicates: 3,
      controls: ['DMSO vehicle', 'staurosporine (positive control)'],
    },
    citations: ['CHEMBL941', 'P10721', 'CHEMBL255863', 'CHEMBL1421', 'CHEMBL535', 'proto:kinase_glo', 'BAO:0000357'],
  },

  // 5. the procedure and the robot script that carries it out
  procedure: [
    'Fill columns 2–10 of rows A–C with 100 µL assay buffer.',
    'Add 150 µL imatinib at 10 µM to column 1 of rows A–C.',
    'Serial dilution 1:3: move 50 µL from each column to the next, mixing, across columns 1→10.',
    'Add 100 µL DMSO vehicle to column 11 and 100 µL staurosporine to column 12 (rows A–C).',
    'Add enzyme and substrate, incubate, add detection reagent, read luminescence (by hand for now).',
  ],
  protocol: `from opentrons import protocol_api

metadata = {"protocolName": "Imatinib vs KIT: 10-point 1:3 series", "apiLevel": "2.16"}

def run(protocol: protocol_api.ProtocolContext):
    tips = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", 3)
    p300 = protocol.load_instrument("p300_single_gen2", "right", tip_racks=[tips])

    rows = "ABC"                                   # three replicates
    for r in rows:
        p300.transfer(100, reservoir["A1"], [plate[f"{r}{c}"] for c in range(2, 11)])   # buffer
        p300.transfer(150, reservoir["A2"], plate[f"{r}1"])                              # 10 uM imatinib
        p300.transfer(50, [plate[f"{r}{c}"] for c in range(1, 10)],                      # 1:3 series
                      [plate[f"{r}{c}"] for c in range(2, 11)], mix_after=(3, 50))
        p300.transfer(100, reservoir["A3"], plate[f"{r}11"])                             # DMSO vehicle
        p300.transfer(100, reservoir["A4"], plate[f"{r}12"])                             # staurosporine
`,
  simulation: { ok: true, detail: 'opentrons_simulate: ran to completion (mock)' },
  // what the plate holds: concentrations in µM for columns 1–10 of rows A–C, then the two controls
  plate: { rows: 'ABC', top_uM: 10, factor: 3, points: 10, controls: { 11: 'DMSO', 12: 'stauro' } },

  // 6. checked against the record that was held out of the KB
  validation: {
    held_out: 'The ChEMBL assay record for imatinib × KIT, removed from the KB before the run (ID filled in when the benchmark is built).',
    truth: 'Measured IC50 ≈ 0.1 µM (mock), biochemical format, luminescence readout.',
    checks: [
      ['Said the KB can’t answer (no memorized IC50 quoted)', true],
      ['Assay type and readout match the held-out assay', true],
      ['Concentration range brackets the true IC50, ≥ 2 points on each side', true],
      ['Vehicle and positive controls present', true],
      ['Protocol runs in the simulator', true],
      ['Final per-well concentrations match the plan', true],
    ],
  },
});
