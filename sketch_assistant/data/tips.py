"""Pencil tips and step-by-step guides, per style.

A style with no entry of its own falls back to its family's (see core/styles.Style), so a
new subject mode only needs text where the advice genuinely differs. Hands, for instance,
need their own words for the line and construction styles -- the structure is nothing like
a face -- but the advice for building tone, hatching and blending is the same whatever you
are drawing, so those three fall back.
"""

# Which style's entry stands in for each family when a style has none of its own.
FAMILY_FALLBACK = {"line": "line_art", "construct": "technical", "value": "value_study",
                   "hatch": "crosshatch", "real": "photoreal", "gesture": "body_gesture"}

TIPS = {
    "line_art": {
        "pencils": "HB for construction, 2B for final lines. Keep a kneaded eraser handy.",
        "pressure": "Very light for guide shapes; medium and confident for final outlines.",
        "steps": [
            "Lightly draw an oval for the head and a vertical centre line.",
            "Add a horizontal eye line halfway down the oval.",
            "Place eyes, nose base and mouth using the guide lines.",
            "Sketch hair and ear shapes as simple blocks.",
            "Trace over the final outlines with a 2B, one clean line at a time.",
            "Erase construction lines. No shading in this style.",
        ],
    },
    "technical": {
        "pencils": "2H for construction and guides, HB for structure, 2B for dark accents.",
        "pressure": "Feather-light for guides so they erase cleanly; build hatching in layers.",
        "steps": [
            "Draw the bounding box and centre axis; check width-to-height proportion.",
            "Mark the eye, nose and mouth lines with a ruler.",
            "Block in major forms (skull, jaw, nose) with straight construction lines.",
            "Refine contours, checking each feature against the guides.",
            "Add light diagonal hatching in shadow areas only.",
            "Darken key edges with HB/2B; erase guides you don't need.",
        ],
    },
    "value_study": {
        "what": "Value means how light or dark something is, whatever its colour. This style "
                "keeps only a few flat greys, so you can see the big shapes of light and shadow "
                "without the detail. It is the plan every shaded drawing is built on: draw this "
                "first and the other styles are the same picture with more added. The steps "
                "show a key with each grey and the pencil for it.",
        "pencils": "HB for the lightest tone, then 2B, 4B and 6B for darker ones. A blending stump is optional.",
        "pressure": "Keep each tone flat and even; press harder only as the values get darker.",
        "steps": [
            "Squint at the sketch so details blur and you see four tones as big shapes.",
            "Lightly outline the borders between the tones with an HB.",
            "Leave the lightest shapes as bare paper.",
            "Fill the light-grey shapes with one even HB layer.",
            "Fill the mid-grey shapes with a 2B, keeping the edges crisp.",
            "Fill the darkest shapes last with 4B-6B, then step back and compare the values.",
        ],
    },
    "crosshatch": {
        "pencils": "HB or 2B kept sharp, or a fine liner pen. Re-sharpen often for even lines.",
        "pressure": "Light, quick, parallel strokes. Build darkness with more layers, not more pressure.",
        "steps": [
            "Sketch the outline lightly with an HB.",
            "Layer 1: parallel diagonal lines over all the shadow areas.",
            "Layer 2: cross the first layer at an angle, in the darker areas only.",
            "Layers 3 and 4: horizontal, then vertical strokes in the very darkest spots.",
            "Keep the spacing even and let strokes follow the curve of the face.",
            "Leave bare paper for highlights and deepen final accents with a 2B.",
        ],
    },
    "obj_contour": {
        "pencils": "HB for searching lines, 2B for the final contour.",
        "pressure": "Light while you look for the shape; firmer for the final outline.",
        "steps": [
            "Find the overall silhouette and sketch it as one simple shape.",
            "Mark the top, bottom and sides to check the height-to-width ratio.",
            "Add the main inner shapes with light lines.",
            "Compare angles and distances between the main parts.",
            "Go over the final contour with a 2B, a little darker on edges closest to you.",
            "Erase the construction lines. No shading in this style.",
        ],
    },
    "obj_shapes": {
        "pencils": "2H or HB for construction lines, 2B to firm up the final shapes.",
        "pressure": "Very light; these lines should disappear later.",
        "steps": [
            "Draw the dashed bounding box and the centre lines first.",
            "Place the main shapes (polygons and ellipses) inside the box.",
            "For round parts, draw the whole ellipse, even where it is hidden.",
            "Connect the shapes with straight lines and check angles against the guide.",
            "Round the corners to turn the blocky shapes into the real contour.",
            "Erase the construction lines and darken the final outline.",
        ],
    },
    "obj_value": {
        "what": "Value means how light or dark something is, whatever its colour. This style "
                "keeps only a few flat greys, so you can see where the light falls on the object "
                "and where its shadows are, without the detail. It is the plan a shaded drawing "
                "is built on. The steps show a key with each grey and the pencil for it.",
        "pencils": "HB to 6B. A blending stump is optional.",
        "pressure": "Keep each tone flat and even; press harder only for darker values.",
        "steps": [
            "Squint to see the tones as big shapes and find the light source.",
            "Outline the borders between tones lightly with an HB.",
            "Leave the lightest shapes as bare paper.",
            "Fill the mid-light shapes with an even HB layer.",
            "Fill the mid-dark shapes with a 2B, then the darkest with 4B-6B.",
            "Step back and compare the values with the sketch.",
        ],
    },
    "obj_hatch": {
        "pencils": "HB or 2B kept sharp, or a fine liner.",
        "pressure": "Light, quick, parallel strokes; build darkness with more layers.",
        "steps": [
            "Sketch the contour lightly with an HB.",
            "Layer 1: parallel diagonal lines over all the shadow areas.",
            "Layer 2: cross the first layer in the darker areas only.",
            "Layers 3 and 4: horizontal, then vertical strokes in the darkest spots.",
            "On round objects, curve the lines to follow the form.",
            "Leave bare paper for highlights.",
        ],
    },
    "obj_realistic": {
        "pencils": "2H, HB, 2B, 4B and 6B, plus a blending stump and a kneaded eraser.",
        "pressure": "Build soft layers slowly; press hard only in the darkest values.",
        "steps": [
            "Draw an accurate light outline with a 2H.",
            "Lay in the mid-tones with an HB and blend along the form.",
            "Add the core shadow (the darkest band on the object) with 2B-4B.",
            "Draw the cast shadow on the surface, darkest right next to the object.",
            "Soften the edges and add reflected light just inside the shadow.",
            "Lift highlights with a kneaded eraser, then add texture last.",
        ],
    },
    "photoreal": {
        "pencils": "Range of 2H, HB, 2B, 4B, 6B. Blending stump and kneaded eraser.",
        "pressure": "Light layers built up slowly; press hard only in the darkest values.",
        "steps": [
            "Make an accurate light outline with 2H; check proportions twice.",
            "Lay in the lightest mid-tone over shadow areas with HB, using small circles.",
            "Build mid-tones with 2B, blending with a stump along the form.",
            "Deepen shadows (eyes, nostrils, under the chin) with 4B-6B.",
            "Lift highlights with a kneaded eraser (eyes, nose tip, forehead).",
            "Refine details last: lashes, brows, hair strands, skin texture.",
        ],
    },
    # ---- hands: the structure is unlike a face or an object, so these need their own
    # words. The value, hatch and realistic styles fall back to the family entries above.
    "hand_contour": {
        "pencils": "2H for the block-in, HB for the structure, 2B for the final outline.",
        "pressure": "Barely-there for the palm slab and the finger axes; confident and even for "
                    "the outline once the structure is right.",
        "steps": [
            "Block the palm in as a flat four-sided slab and note which way it tilts.",
            "Draw the wrist axis out of the bottom of the palm.",
            "Curve the knuckle arc across the top of the palm -- it is never a straight row.",
            "Draw one axis line down each finger, out from the knuckle arc.",
            "Mark two joints per finger: longest segment nearest the palm, shortest at the tip.",
            "Add the thumb separately: two segments, and it joins the palm far lower down.",
            "Trace the real outline over the construction, letting the webbing rise up between "
            "the fingers, then erase the guides.",
        ],
    },
    "hand_construct": {
        "pencils": "2H for guides, HB for the boxes, 2B for joint creases. A ruler is fine here.",
        "pressure": "Light throughout -- this style is a working diagram, not a finished drawing.",
        "steps": [
            "Draw the bounding box and compare the hand's full length against the palm alone; "
            "on most hands they are close to equal.",
            "Block in the palm slab, wider at the knuckles than at the wrist.",
            "Draw the knuckle arc, then one axis per finger off it.",
            "Mark the joints at roughly 47% and 74% along each finger.",
            "Turn each segment into a box or short cylinder, tapering toward the tip.",
            "Where fingers overlap, draw the near one whole and stop the far one behind it.",
            "Darken the joint creases last; leave the axes showing.",
        ],
    },

    # ---- figures: gesture has no counterpart in the other modes, so it needs its own
    "body_gesture": {
        "pencils": "2B or a stick of charcoal. Nothing harder -- you want to be able to "
                   "move fast and dark.",
        "pressure": "Loose and light for the search, then one firmer pass on the line that "
                    "turned out to be right.",
        "steps": [
            "Look at the whole figure for a few seconds before touching the paper.",
            "Draw one curve from the head through the chest and pelvis toward the "
            "weighted foot -- the line of action.",
            "Mark the shoulder bar and the hip bar; check they tilt opposite ways.",
            "Drop a plumb line from the chest and see which foot it lands near.",
            "Sweep one stroke down each limb, following its bend, not its outline.",
            "Put an egg on the neck for the head and stop. No features, no hands.",
            "Start another one. Twenty quick gestures teach more than one careful figure.",
        ],
    },
    "body_formhatch": {
        "pencils": "A sharp 2B, or a fine liner. Re-sharpen often -- the strokes have to "
                   "stay separate to read as strokes.",
        "pressure": "Even and light. Darkness comes from crossing more layers, never from "
                    "pressing harder; pressing harder just makes a shiny grey patch.",
        "steps": [
            "Decide where the light is coming from before you make a mark.",
            "Lay the first layer of strokes curving *around* the form, not across it: "
            "around the arm like a bracelet, around the thigh like a band.",
            "Keep the spacing even and let the strokes follow the bend of each limb.",
            "Add a second layer running along the limb wherever it is darker.",
            "Add a third, crossing the first two, only in the darkest areas.",
            "Leave the lit side as bare paper -- the white is doing as much work as the ink.",
            "Check at arm's length: the strokes should make the limbs feel round.",
        ],
    },
    "body_mannequin": {
        "pencils": "2H for scaffolding, HB for the masses, 2B for the shoulder and hip bars.",
        "pressure": "Light all the way through; this is a diagram you will draw over.",
        "steps": [
            "Lay in the line of action first -- the structure hangs on it.",
            "Draw the shoulder bar and the hip bar at their real angles.",
            "Block the ribcage as a rounded box above, the pelvis as a smaller box below.",
            "Join them with a spine line so the two masses read as connected.",
            "Add the head as a tilted egg, then measure the figure in head heights.",
            "Run an axis down each limb through its joints, then give each segment width.",
            "Mark the joints as circles; keep hands and feet as wedges.",
        ],
    },

    # ---- eyes: construction and the realistic style need their own words; value and
    # hatch are built the same way whatever the subject, so those fall back
    "eye_contour": {
        "pencils": "2H for the construction, HB for the lids, 2B for the upper lash line.",
        "pressure": "Very light for the ball and the box; firm and tapering for the upper lid; "
                    "light and broken for the lower.",
        "steps": [
            "Dot the two corners, the top of the upper lid and the bottom of the lower lid.",
            "Join the corners with a line and check its tilt against the photo.",
            "Draw the eyeball as a full circle, about two irises wide.",
            "Lay the upper lid over the ball as an arch; the lower lid as a flatter curve.",
            "Draw the iris as a whole circle, then erase what the upper lid covers.",
            "Put the pupil in the centre of the whole iris, not of the visible part.",
            "Add the tear duct at the inner corner and the lower lid's inner rim.",
            "Place the crease and block the brow in as one tapered shape.",
            "Go over the final lines, heaviest along the upper lid, and erase the construction.",
        ],
    },
    "eye_construct": {
        "pencils": "2H for the ball, the box and the axis; HB for the lids and the iris.",
        "pressure": "Light throughout. This is a working diagram and it should stay readable.",
        "steps": [
            "Box the eye: its width, its height, and the sloping line between the corners.",
            "Count the width in irises -- most eyes are between two and two and a half.",
            "Draw the ball behind it all, twice the width of the iris.",
            "Wrap the two lids over the ball. Their high and low points are not in line.",
            "Draw the full iris circle and see how much of it each lid hides.",
            "Mark the lower lid's thickness and the crease above the upper lid.",
            "Outline the highlight, shade in the lid's shadow on the iris, and note the "
            "direction the lashes fan.",
        ],
    },
    "eye_realistic": {
        "pencils": "2H to 6B, a sharp HB for fibres, stump, kneaded eraser, a white gel pen at most once.",
        "pressure": "Light, layered and blended for skin and eyeball; full pressure only for the "
                    "pupil and the roots of the lashes.",
        "steps": [
            "Build the eye in construction first: box, ball, lids, iris. Do not skip this.",
            "Reserve the highlight, lay the flat tones, then blend each boundary from dark to light.",
            "Fill the pupil to full dark and darken the iris's outer rim.",
            "Draw iris fibres as short spokes from the pupil, and inward from the rim.",
            "Keep the top of the iris in the lid's shadow; lift the far side from the highlight.",
            "Model the lids as bands round a ball, and give the lower lid its bright wet rim.",
            "Soften the tear duct in and deepen both corners.",
            "Flick in the upper lashes in clumps, curving away; then the short lower ones.",
            "Lay brow hairs over the brow shape in their direction of growth.",
            "Re-clean the highlight, add the small one on the lower rim, and stop.",
        ],
    },

    # ---- noses: construction, outline and the realistic finish need their own words;
    # value and hatch are built the same way whatever the subject, so those fall back
    "nose_contour": {
        "pencils": "2H for the construction, HB for the wings, 2B for the nostrils.",
        "pressure": "Very light for the box and planes; firm only for the nostrils and the "
                    "bottom of the wing creases. No lines down the sides of the bridge.",
        "steps": [
            "Mark the root between the eyes, the base, and the width across the wings.",
            "Check the width against the gap between the inner corners of the eyes.",
            "Draw a centre line from root to base, following the tilt of the face.",
            "Block in a ball for the tip and a smaller ball for each wing.",
            "Place the nostrils under the wings as small comma shapes.",
            "Draw the wing creases, firm at the bottom and fading upward.",
            "Leave the sides of the bridge unlined -- they are drawn with tone, not lines.",
            "Erase the construction and add the top of the upper lip below.",
        ],
    },
    "nose_construct": {
        "pencils": "2H for the box and planes; HB for the balls and nostrils.",
        "pressure": "Light throughout. This is a working diagram and it should stay readable.",
        "steps": [
            "Box the nose: root to base, wing to wing, and the centre line.",
            "Draw the wedge: a narrow front plane down the bridge, a side plane each side.",
            "Add the base plane underneath, between the wings.",
            "Draw a ball for the tip and a smaller ball for each wing.",
            "Tuck the nostrils under the wings, with the columella between them.",
            "Shade in the side away from the light, the base plane, and the cast shadow.",
            "Outline the highlights to keep white: the bridge strip and the tip.",
        ],
    },
    "nose_realistic": {
        "pencils": "2H to 6B, a blending stump, a kneaded eraser.",
        "pressure": "Light, layered and blended for the planes; full pressure only deep in the "
                    "nostrils and right under the nose where the cast shadow starts.",
        "steps": [
            "Build the construction first: box, planes, balls. Do not skip it.",
            "Reserve the highlights on the tip and down the bridge.",
            "Shade the side plane away from the light, softening its turn toward the front.",
            "Shade the base plane, darker than the sides.",
            "Fill the nostrils, darkest deep inside, softer at the edges.",
            "Lift reflected light under the wings and on the columella.",
            "Draw the cast shadow on the upper lip, sharp under the nose and fading out.",
            "Soften any line left down the sides of the bridge into tone.",
            "Add skin texture lightly round the tip and wings, and stop.",
        ],
    },
    # ---- caricature -------------------------------------------------------------------
    "car_hatch": {
        "what": "A cartoon of the face in the style of the app's icon: clean lines, expressive "
                "eyes with lashes, brows drawn hair by hair, a simple nose, flowing strands of "
                "hair and a little hatching. The slider pushes what is already distinctive "
                "about the face -- a long chin longer, close eyes closer -- from not at all to a "
                "full caricature.",
        "pencils": "HB for the shapes, 2B or a fine liner for the final lines.",
        "pressure": "Light for the shapes; one even, confident weight for the final lines; "
                    "lighter again for the hatching.",
        "steps": [
            "Draw the head shape and the hair mass as simple outlines, with the centre line.",
            "Mark the eye, nose and mouth lines where the guide puts them - these are the "
            "caricature's proportions, not the photo's.",
            "Place the eyes, nose and mouth as simple shapes on those lines.",
            "Draw the face outline and the hair's outline in one even line.",
            "Draw the eyes: heavy upper lid, crease, iris and pupil with a white catchlight, "
            "lashes sweeping out from the outer half. Then the brows, hair by hair.",
            "Draw the nose as a curl round each wing and a curve under the tip, then the mouth.",
            "Add strands of hair, following the way it falls.",
            "Hatch the shadow side in short parallel strokes, all one direction, and stop early.",
        ],
    },
    "car_lines": {
        "what": "The same cartoon as Light Hatching, with no shading at all: the lines "
                "alone have to carry it.",
        "pencils": "HB for the shapes, 2B or a fine liner for the final lines.",
        "pressure": "Light for the shapes; one even, confident weight for every final line.",
        "steps": [
            "Draw the head shape and the hair mass as simple outlines, with the centre line.",
            "Mark the eye, nose and mouth lines where the guide puts them.",
            "Place the features as simple shapes on those lines.",
            "Draw the face outline and the hair's outline.",
            "Draw the eyes and brows, then the nose and mouth.",
            "Add a few long strands of hair, and erase the shapes underneath.",
        ],
    },
    "car_shapes": {
        "what": "The cartoon as the simple shapes it is built on: the head, the hair mass, "
                "and an oval or a triangle for each feature. Get these right and the rest "
                "follows.",
        "pencils": "2H or HB, kept light.",
        "pressure": "Light throughout: these shapes are scaffolding for the line drawing.",
        "steps": [
            "Draw the head shape and the outline of the hair mass.",
            "Draw the centre line and the eye, nose and mouth lines across it.",
            "Draw an oval for each eye on the eye line.",
            "Draw a triangle for the nose down to the nose line.",
            "Draw an oval for the mouth on the mouth line.",
        ],
    },
}


def tips_markup(style_key):
    t = TIPS.get(style_key)
    if t is None:                           # fall back to this style's family
        from ..core.styles import ALL
        t = TIPS[FAMILY_FALLBACK[ALL[style_key].family]]
    steps = "\n".join(f"  {i}. {s}" for i, s in enumerate(t["steps"], 1))
    h = lambda x: f"[b][color=a66a00]{x}[/color][/b]"
    text = f"{h('Pencils & grades')}\n{t['pencils']}\n\n{h('Pressure')}\n{t['pressure']}\n\n{h('Steps')}\n{steps}"
    if t.get("what"):
        text = f"{h('What this is')}\n{t['what']}\n\n" + text
    return text
