import json, os
p = r'D:\Video\From Need to Tool\why-clay-in-your-pencil\beats.json'
with open(p, encoding='utf-8-sig') as f: d=json.load(f)
scenes = {
'B01': [
('A sharpened wooden pencil beside two test marks: one pale and narrow, one dark and broad; maker holds it at a writing desk.', 'The visible core controls the kind of line.'),
('Close cutaway of the pencil tip; compact black core centered in pale cedar, hand steadies the pencil.', 'Show that the core sits inside wood.'),
('Small neat graphite pieces and pale clay grains side by side on a workshop board; a maker compares them by touch.', 'The added material is intentional.'),
('A pencil point touches paper and leaves a light line while a dark sample line sits nearby.', 'Two different useful marks.'),
('A hand draws with a soft graphite pencil; the mark grows darker under a broad stroke.', 'A softer core can make a darker mark.'),
('A short graphite stick rests beside a sharpened pencil; a craft worker examines the fragile loose material.', 'Useful graphite still has to be made workable.'),
('Simple educational cutaway: graphite sheets stacked like thin plates, strong bonds within each plate and loose spacing between plates.', 'Layered carbon explains why particles rub away.'),
('Magnified graphite flakes transfer from pencil point onto paper fibers; clear scientific illustration, no invented numerical labels.', 'Tiny particles make the visible line.'),
('A palm smears a graphite test mark on paper at a drawing desk.', 'Graphite can smear when rubbed.'),
('Pencil shavings curl beside a shorter pencil after sharpening; hands continue writing.', 'Writing consumes the point.'),
('A craftsperson holds a finished pencil and loose graphite, considering how to contain the material.', 'The maker’s problem is containment and control.'),
('Open wooden pencil cutaway leads visually toward small graphite and clay portions on a clean bench.', 'The title question moves inside the pencil.')],
'B02': [
('Illustrated map of England with the Lake District and Borrowdale clearly highlighted, restrained coastline and no extra labels.', 'Orient the Borrowdale source.'),
('Borrowdale hillside with exposed dark graphite seam, workers collecting a small piece; calm grounded landscape.', 'A local deposit supplied usable graphite.'),
('Worker carefully cuts a solid graphite block into writing sticks on a simple bench.', 'Some graphite could be cut into sticks.'),
('Close view of a graphite stick being tested on paper; dark line appears beneath the hand.', 'The material had a useful writing property.'),
('A loose graphite stick wrapped in cord to protect fingers, hand writes on paper.', 'Wrapping supports handling.'),
('A graphite stick fitted into a simple wooden holder, shown in a workshop before the 1790s.', 'Wooden pencil cases predate Conté.'),
('A small set of early wooden pencils beside a loose graphite stick; maker sharpens one with a knife.', 'The case solved a different practical task.'),
('Map highlights Borrowdale relative to the English Channel and northern France; restrained geographic inset.', 'The source and the French shortage were separated by the Channel.'),
('A maker tests two graphite fragments on a scrap of paper before choosing material for a writing stick.', 'Not every deposit fragment serves the same workshop purpose.'),
('A merchant’s workbench with a few graphite sticks and an empty place where more were expected; illustrative supply limitation.', 'Material supply could constrain production.'),
('Chibi local historian points to Borrowdale landscape on a map while a graphite sample rests nearby; no written legend.', 'The place is remembered through local traditions.'),
('Graphite block, cut stick, wrapped stick, and wooden pencil arranged as distinct material forms, not a timeline claim.', 'Finding graphite and making a useful pencil were separate steps.'),
('A maker tests a pencil core against paper and inspects its mark, connecting deposit properties to workshop use.', 'The material’s physical character mattered.')],
'B03': [
('Map of France in 1794 with a simple highlighted Paris region and English Channel; no invented borders or route data.', 'Orient the wartime French context.'),
('Two workshops separated by a simple Channel map; a small graphite supply bundle sits on the English side, French pencil maker waits with empty bench.', 'Disrupted English supply contributed to shortage.'),
('A French pencil maker examines an existing wooden pencil and an empty graphite tray.', 'The task was replacement supply, not inventing writing.'),
('Powdered graphite prepared on a stone slab by a craft worker, period-neutral reconstruction without exact portrait.', 'Powder offered a different starting form.'),
('A maker measures graphite powder and clay in two small bowls, no numbers or text.', 'Conté’s process combined two materials.'),
('Hands blend black powder and pale clay into an even mixture on a board.', 'Mixing creates a workable compound.'),
('Mixture pressed into a simple narrow core shape, close view of hand and tool.', 'The core must hold a useful shape.'),
('A row of newly formed soft cores rests on a drying board, maker moves one carefully.', 'Forming is followed by drying.'),
('Fired cores emerge from a small workshop kiln, maker checks one after cooling; illustrative reconstruction.', 'Firing changes the prepared core.'),
('Plain patent document and a separate finished pencil on a table, no fake handwriting or seal.', 'The process was patented in 1795.'),
('A wooden pencil opened to show a formed core made from a mixture, beside loose graphite pieces.', 'The change happened inside the familiar case.')],
'B04': [
('Two graphite-and-clay cores shown as a clean side-by-side educational comparison, proportions differ without numeric labels.', 'Composition can vary.'),
('A darker, softer core leaves a broad black stroke on paper beneath a drawing hand.', 'More graphite generally makes a softer, darker core.'),
('A harder core draws a fine pale guide line beside a sketch outline.', 'More clay generally makes a harder core.'),
('Two hands select different pencils for different drawing tasks at one studio desk.', 'The mixture creates choices for makers and users.'),
('Close-up of a pencil marked H beside a fine light construction line; exact single letter only.', 'H names the harder direction.'),
('Close-up of a pencil marked B beside a dark shaded patch; exact single letter only.', 'B names the softer, blacker direction.'),
('A pencil marked HB rests between the H and B examples, balanced composition.', 'HB sits between those directions.'),
('A diagram-like row of cores grows progressively harder to softer; avoid numbers and scales.', 'The range is a set of working choices.'),
('Artist uses a hard pencil to sketch a light geometric guide line.', 'A harder pencil suits light precise work.'),
('Artist uses a softer pencil to shade a broad shadow beside the guide sketch.', 'A softer pencil suits dark shading.'),
('A hand tests two pencil marks with different pressure; both vary but core difference remains visible.', 'Pressure matters, but core choice adds another control.'),
('Close cutaway shows graphite and clay mixed through a single core, no false layered structure.', 'Clay is mixed into the core, not a separate stripe.'),
('Finished range of pencils and two sample marks on a simple drawing board, maker chooses deliberately.', 'The point is prepared for a particular task.')],
'B05': [
('Modern production room with worker preparing graphite, clay and water in a controlled mixing vessel.', 'A modern manufacturer describes these ingredients.'),
('Close view of graphite powder, pale clay and measured water entering a mixer; no numbers or labels.', 'The ingredients are mixed.'),
('A press forms a continuous pencil core from the wet mixture; worker monitors the machine.', 'Pressure forms the core shape.'),
('Fresh soft cores laid carefully on racks before drying; worker checks spacing.', 'The newly formed mixture remains soft.'),
('Drying racks in a clean workshop, cores visibly firming; no dramatic transformation implied.', 'Drying prepares cores for heat treatment.'),
('Cores enter a kiln on a tray; worker operates it safely at a distance.', 'Firing is part of the process.'),
('Finished fired cores receive a thin wax treatment in a modern facility, clean close-up.', 'One maker adds wax after firing today.'),
('Modern worker inspects cedar boards and thin slats at a separate wood-preparation station.', 'Wood preparation is a separate production line.'),
('Thin wooden slats are sorted and defects removed by worker beside a machine.', 'The casing needs its own materials and preparation.')],
'B06': [
('Groove cutting machine forms parallel channels in a cedar slat while worker guides the board.', 'Cores sit in grooves rather than a long drilled hole.'),
('Worker lays finished cores into parallel grooves in a wooden slat, precise hands visible.', 'Cores are fitted into the grooves.'),
('Second grooved slat lowered over the first to create a wooden sandwich with several cores inside.', 'Two prepared slats enclose several cores.'),
('Clamped pencil sandwich rests while glue sets; worker checks alignment.', 'The assembly must bond.'),
('The joined board enters a shaping cutter that separates individual pencil outlines.', 'The block is shaped into pencil bodies.'),
('Three separate pencil bodies with round, triangular and hexagonal cross-sections on a bench.', 'The process supports different body shapes.'),
('Workers paint and mark pencil bodies on a production line, no invented brand text.', 'Finishing follows shaping.'),
('An eraser and metal holder are fitted to one pencil; another remains plain.', 'Some products add a ferrule and eraser.'),
('Historical workshop reconstruction with workers preparing boards and laying cores by hand, nineteenth-century clothing kept modest.', 'A nineteenth-century account describes the same basic assembly.'),
('A later machine assists in joining pencil parts while worker supervises; no exact historical machine claim.', 'Machinery changed how tasks were organized.')],
'B07': [
('Material relationship diagram: graphite, clay, fuel and wood feed a pencil workshop, shown as icons without numerical flow.', 'The process changed one dependency, not every material need.'),
('English graphite block fades from central position as several material inputs sit around a French-style workshop.', 'Suitable English graphite was no longer the only starting form.'),
('Maker handles graphite and clay near a kiln and wood slats, several requirements remain visible.', 'Graphite, clay, fuel, wood, tools and skill remain necessary.'),
('Small workshop produces a batch of pencils; workers repeat core and casing tasks.', 'Conté also established manufacture.'),
('French industrial exhibition hall in 1798 with pencils displayed on a plain table, no invented signage.', 'His pencils received exhibition recognition.'),
('Simple timeline with 1795 patent and 1798 exhibition points, exact dates only.', 'Patent and exhibition are distinct milestones.'),
('Modern quality worker checks pencil cores for strength without staged failure spectacle.', 'Production required quality control.'),
('Cutaway of a later bonded core secured along a pencil body, clear glue interface, no false mechanism.', 'Later makers developed bonding to reduce breakage.')],
'B08': [
('Graphite line on paper with a hand brushing across it and leaving a visible smudge, conservation-style demonstration.', 'Graphite marks can smear.'),
('A drawing protected under a sheet while an exposed graphite sketch remains vulnerable to rubbing.', 'Preserving a graphite drawing takes care.'),
('Artist adjusts a graphite sketch with a soft eraser, practical and non-dramatic.', 'Changeability is useful during drawing.'),
('Pencil cutaway beside graphite and clay particles, core shown as a uniform mixed material.', 'Clay helps form a stable working core.'),
('Two pencil cores produce a fine pale line and dark shaded patch, side by side.', 'Composition helps determine the mark.'),
('A pencil maker’s hands prepare a core mixture at a workbench, action linked to production.', 'Conté’s response addressed a supply problem.'),
('A person chooses between two pencils before starting a drawing, both tools clear and ordinary.', 'The recipe reaches an everyday choice.'),
('Final close view of a sharpened pencil point touching paper, fresh line beside small shavings.', 'Each line uses a little of the point.')]
}
with open(p, encoding='utf-8-sig') as f: d=json.load(f)
d['visual_bible']={
 'style':'Original Chibi 2D educational stills, hand-inked charcoal outlines, restrained expressive people, clean silhouettes, uncluttered explanatory compositions.',
 'palette':'Pale paper, warm wood, clay ochre, graphite black; episode-specific emphasis, no channel-template palette.',
 'continuity':'Pencil core is a uniform graphite-and-clay mixture enclosed by wood. Graphite source is Borrowdale, Lake District; Conté setting is France in 1794–1798. Modern manufacturing scenes are clearly contemporary. No invented portrait, dialogue, documents, supply quantities, ratio data or first-adoption claims.',
 'camera':'Calm hold for diagrams and close mechanisms; subtle purpose-led move for human tasks and geographic orientation. Frozen actions must be visible in each still.'}
counts=[12,13,11,13,9,10,8,8]
for beat,n in zip(d['beats'],counts):
  items=scenes[beat['id']]
  assert len(items)==n, (beat['id'],len(items),n)
  dur=float(beat['narration_dur'])/n
  beat['shots']=[]
  for i,(scene,purpose) in enumerate(items,1):
    beat['shots'].append({
      'id':f'S{i:02d}', 'dur':round(dur,4), 'scene':scene,
      'visual_intent':{'purpose':purpose,'representation':'original Chibi 2D illustration or clean educational diagram','continuity':'Use the period, object state and distinction stated in this shot; modern illustrations are contemporary.'},
      'people_policy':'contextual' if any(w in scene.lower() for w in ['worker','maker','artist','hand','person','craft','merchant','historian']) else 'none',
      'image_text_policy':'none',
      'animation':{'start':purpose,'keyframe':scene,'action':purpose,'end':purpose,'camera':'auto','framing':'one clear focal action or relationship; simple phone-readable composition','continuity':'No unsupported labels, exact portrait or implied movement between states.'}
    })
with open(p,'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
print('shots',sum(len(b['shots']) for b in d['beats']),'seconds',sum(float(s['dur']) for b in d['beats'] for s in b['shots']))
