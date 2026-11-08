// The problem statement as a picture, starting from the person: a scientist's question goes into the missing link
// (the "?" in the middle), which draws on the world's scientific literature (left) and an automated cloud lab
// (right): it sends the lab the next experiment, takes the lab's feedback, and answers the scientist. The shapes
// are manim-web; the labels and the speech bubble are HTML placed at the same world points.
// Steps: 1 the scientist asks; the question goes into an empty "?" · 2 the literature: prior knowledge, but no
// answer · 3 the cloud lab (a well plate) · 4 the "?" sends the next experiment to the lab, over the top · 5 the
// lab's feedback comes back · 6 the answer goes back to the scientist, closing the loop.
{
// world units (16 x 9, origin at the centre, y up) -> a point in the frame, for the HTML labels
const at = (x, y) => `left: ${(x + 8) / 16 * 100}%; top: ${(4.5 - y) / 9 * 100}%;`;

const LIT = [-5.2, 0.8], LAB = [5.2, 0.8], GAP = [0, 0.8], USER = [0, -2.25];

Deck.slide('loop', {
  steps: 6,
  notes: 'It starts with a person: a scientist asks a question nobody has answered yet. Two things already exist: '
    + 'more literature than anyone can read, and labs that run experiments automatically. What is missing is the '
    + 'link between them: from the question and what is already known, decide what to test next, send it to the '
    + 'lab, learn from the result, and answer the scientist. That link is what we are building.',
  mount(frame, { css, esc }) {
    css(`
      /* translate, not transform: .reveal-in animates transform */
      .lp-label { position: absolute; translate: -50% 0; text-align: center; white-space: nowrap; }
      .lp-name { font-size: var(--t-body); font-weight: 700; }
      .lp-sub { font-size: var(--t-small); color: var(--muted); }
      .lp-edge { position: absolute; translate: -50% -50%; width: 15%; text-align: center; line-height: 1.15;
        font-size: var(--t-small); color: var(--muted); }
      .lp-edge.lp-next { width: auto; white-space: nowrap; color: var(--accent); font-weight: 700; }
      /* labels beside the vertical question / answer arrows: ending at (l) or starting from (r) their point */
      .lp-edge.lp-l, .lp-edge.lp-r { width: auto; white-space: nowrap; }
      .lp-edge.lp-l { translate: -100% -50%; text-align: right; }
      .lp-edge.lp-r { translate: 0 -50%; text-align: left; }
      .lp-edge.lp-answer { color: var(--accent); font-weight: 700; }
      .lp-bubble { position: absolute; translate: 0 -50%; white-space: nowrap; font-size: var(--t-small);
        font-style: italic; padding: .35em .8em; border-radius: .9em; background: var(--bg);
        border: 1.5px solid color-mix(in srgb, var(--fg) 35%, transparent); }
      .lp-bubble::before { content: ''; position: absolute; left: -.45em; top: 50%; width: .7em; height: .7em;
        translate: 0 -50%; rotate: 45deg; background: var(--bg);
        border-left: 1.5px solid color-mix(in srgb, var(--fg) 35%, transparent);
        border-bottom: 1.5px solid color-mix(in srgb, var(--fg) 35%, transparent); }
    `);
    const label = (x, y, name, sub, from) => `<div class="lp-label reveal-in" data-from="${from}" style="${at(x, y)}">
      <div class="lp-name">${esc(name)}</div>${sub ? `<div class="lp-sub">${esc(sub)}</div>` : ''}</div>`;
    const edge = (x, y, text, from, extra = '') =>
      `<div class="lp-edge ${extra} reveal-in" data-from="${from}" style="${at(x, y)}">${esc(text)}</div>`;

    frame.innerHTML = `
      <div class="deck-stage"></div>
      <h2 class="deck-heading reveal-in" data-from="1">What should we test next?</h2>
      ${label(USER[0] - 2.1, USER[1] + 0.05, 'A scientist', 'asks in plain language', 1)}
      <div class="lp-bubble reveal-in" data-from="1" style="${at(USER[0] + 0.85, USER[1] + 0.2)} --i:1">“Will it spare gut microbes?”</div>
      ${edge(-0.55, -0.95, 'question', 1, 'lp-l')}
      ${label(LIT[0], LIT[1] - 1.55, 'Scientific literature', 'more papers than anyone can read', 2)}
      ${edge(-2.6, LIT[1] + 0.65, 'prior knowledge, but no answer', 2)}
      ${label(LAB[0], LAB[1] - 1.55, 'Automated experimentation', 'the cloud lab', 3)}
      ${edge(2.5, GAP[1] + 2.45, 'the next experiment', 4, 'lp-next')}
      ${edge(2.45, GAP[1] + 0.65, 'experimental feedback', 5)}
      ${edge(0.55, -0.95, 'answer', 6, 'lp-r lp-answer')}
      <p class="deck-caption reveal-in" data-from="6"><span class="deck-accent">The missing link:</span>
        turn a scientist’s question, prior knowledge and lab feedback into the next experiment.</p>`;

    const stage = Deck.manim(frame.querySelector('.deck-stage'), {
      build: ({ M, P }) => {
        // the scientist: a head over rounded shoulders
        const person = [
          new M.Circle({ radius: 0.27, color: P.fg, fillOpacity: 0.85, strokeWidth: 3 }).moveTo([USER[0], USER[1] + 0.2, 0]),
          new M.RoundedRectangle({ width: 0.95, height: 0.5, cornerRadius: 0.24, color: P.fg, fillOpacity: 0.85,
            strokeWidth: 3 }).moveTo([USER[0], USER[1] - 0.38, 0]),
        ];

        // a fanned stack of papers, the top one with a few lines of "text"
        const papers = [0, 1, 2, 3, 4].map((k) => new M.RoundedRectangle({ width: 1.5, height: 1.95,
          cornerRadius: 0.08, color: P.series[1], fillOpacity: 0.12 + 0.04 * k, strokeWidth: 3 })
          .moveTo([LIT[0] - 0.36 + 0.18 * k, LIT[1] + 0.3 - 0.15 * k, 0]));
        const top = [LIT[0] + 0.36, LIT[1] - 0.3];
        const lines = [0.55, 0.3, 0.05, -0.2, -0.45].map((dy, k) => new M.Line({
          start: [top[0] - 0.5, top[1] + dy, 0], end: [top[0] + (k === 4 ? 0.1 : 0.5), top[1] + dy, 0],
          color: P.series[1], strokeWidth: 3 }));

        // the cloud lab as a well plate: a rounded frame with a 3 x 4 grid of wells
        const plate = new M.RoundedRectangle({ width: 2.5, height: 1.75, cornerRadius: 0.2, color: P.series[3],
          fillOpacity: 0.12, strokeWidth: 4 }).moveTo([LAB[0], LAB[1], 0]);
        const wells = [];
        for (let r = 0; r < 3; r++) {
          for (let c = 0; c < 4; c++) {
            wells.push(new M.Circle({ radius: 0.17, color: P.series[3], fillOpacity: (r * 4 + c) % 3 ? 0.15 : 0.7,
              strokeWidth: 3 }).moveTo([LAB[0] - 0.84 + 0.56 * c, LAB[1] + 0.48 - 0.48 * r, 0]));
          }
        }

        // the gap: a dashed circle with a question mark
        // (DashedVMobject dashes the circle's own points and ignores where it was moved, so move the dashes)
        const ring = new M.DashedVMobject({ vmobject: new M.Circle({ radius: 0.95, color: P.accent, strokeWidth: 5 }),
          numDashes: 22, dashRatio: 0.55 }).moveTo([GAP[0], GAP[1], 0]);
        const mark = new M.Text({ text: '?', fontSize: 110, fontFamily: 'Lato', color: P.accent })
          .moveTo([GAP[0], GAP[1], 0]);

        // straight arrows: the question up into the gap and the answer back down, beside each other; what is known
        // and the lab's feedback in from either side. The next experiment arcs over the top from the gap to the lab
        // (a Bézier plus a tip along its end tangent: M.CurvedArrow fills its arc).
        const arrow = (start, end, color) => new M.Arrow({ start: [...start, 0], end: [...end, 0], color,
          strokeWidth: 4, tipLength: 0.3, tipWidth: 0.2 });
        const question = arrow([USER[0] - 0.3, USER[1] + 0.6], [GAP[0] - 0.3, GAP[1] - 0.98], P.fg);
        const answer = arrow([GAP[0] + 0.3, GAP[1] - 0.98], [USER[0] + 0.3, USER[1] + 0.6], P.accent);
        const known = arrow([LIT[0] + 1.25, LIT[1]], [GAP[0] - 1.15, GAP[1]], P.muted);
        const feedback = arrow([LAB[0] - 1.4, LAB[1]], [GAP[0] + 1.15, GAP[1]], P.muted);
        const c = [[GAP[0] + 0.35, GAP[1] + 1.05], [GAP[0] + 1.2, GAP[1] + 2.3], [LAB[0] - 1.4, LAB[1] + 2.3],
          [LAB[0] - 0.6, LAB[1] + 1.05]];
        const arc = new M.CubicBezier({ points: c.map((p) => [...p, 0]), color: P.accent, strokeWidth: 6 });
        const [dx, dy] = [c[3][0] - c[2][0], c[3][1] - c[2][1]], n = Math.hypot(dx, dy), [ux, uy] = [dx / n, dy / n];
        const base = [c[3][0] - 0.38 * ux, c[3][1] - 0.38 * uy];
        const tip = new M.Polygon({ vertices: [[...c[3], 0], [base[0] - 0.2 * uy, base[1] + 0.2 * ux, 0],
          [base[0] + 0.2 * uy, base[1] - 0.2 * ux, 0]], color: P.accent, fillOpacity: 1, strokeWidth: 2 });

        return { person, papers, lines, plate, wells, ring, mark, question, answer, known, feedback, arc, tip };
      },
      steps: [
        async ({ person, question, ring, mark }, { M, play }) => {
          await play(...person.map((m) => new M.FadeIn(m)));
          await play(new M.GrowArrow(question));
          await play(new M.Create(ring), new M.FadeIn(mark));
        },
        async ({ papers, lines, known }, { M, play }) => {
          await play(new M.LaggedStart([...papers, ...lines].map((m) => new M.FadeIn(m)), { lagRatio: 0.12 }));
          await play(new M.GrowArrow(known));
        },
        ({ plate, wells }, { M }) => [new M.Create(plate),
          new M.LaggedStart(wells.map((w) => new M.GrowFromCenter(w)), { lagRatio: 0.08 })],
        async ({ mark, arc, tip }, { M, play }) => {
          await play(new M.Indicate(mark));
          await play(new M.Create(arc, { duration: 1 }));
          await play(new M.FadeIn(tip, { duration: 0.3 }));
        },
        ({ feedback }, { M }) => [new M.GrowArrow(feedback)],
        async ({ mark, answer }, { M, play }) => {
          await play(new M.Indicate(mark));
          await play(new M.GrowArrow(answer));
        },
      ],
    });

    return {
      enter(step, animate) { Deck.show(frame, step, animate); return stage.go(step, animate); },
      freeze: stage.freeze,
      destroy: stage.dispose,
    };
  },
});
}
