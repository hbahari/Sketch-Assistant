"""Per-stage instructions: which pencil, which technique, what to actually do.

Keyed by the stage ids produced in core/steps.py, so the words and the picture can never
drift apart.

`finish` is the one stage whose advice depends on the chosen style rather than the stage.
It is keyed by style *family* (see core/styles.Style), so Line Art in Portrait and Contour
in Hands share one entry, with FINISH_OVERRIDE holding the cases where a subject really
does need different words. That way a new subject mode needs new text only where the
advice actually changes.
"""

STEPS = {
    # ---- portrait -------------------------------------------------------------------
    "construction": {
        "pencil": "2H, or an HB held almost flat",
        "technique": "Ghosting: swing your hand through the shape two or three times above the "
                     "paper before letting the pencil touch it.",
        "text": "Draw the oval for the skull, then the centre line down it. This line bends with "
                "the head, so follow the one in the guide rather than a straight vertical. Add "
                "the eye, nose and mouth lines across it. Keep every one of these faint enough "
                "to erase later: they are scaffolding, not drawing.",
    },
    "eyes": {
        "pencil": "HB to place them, 2B for the pupil and the lash line",
        "technique": "Measure before you commit. The gap between the eyes is almost exactly one "
                     "eye wide, and both eyes sit on the same line even when the head is tilted.",
        "text": "Start with the upper lid, which is the heaviest line on the whole face, and let "
                "it taper as it reaches the outer corner. Add the lower lid more lightly. Darken "
                "the pupil last, and leave a tiny patch of white paper for the highlight.",
    },
    "nose": {
        "pencil": "HB throughout, 2B only under the tip",
        "technique": "Draw the shadow, not an outline. A nose has almost no edges, so a hard "
                     "line round it is the commonest beginner's mistake.",
        "text": "Mark the two nostrils and the shadow beneath the tip first, since those are the "
                "darkest parts. Then suggest the bridge with the faintest possible tone down one "
                "side. If you can see a continuous line around the nose in your drawing, lighten it.",
    },
    "mouth": {
        "pencil": "HB for the lips, 2B for the line between them",
        "technique": "The line where the lips meet is the darkest and sharpest mark; the outer "
                     "edges of the lips are soft and should almost disappear.",
        "text": "Draw that centre line first, following its slight curve. Build the upper lip "
                "above it and the lower lip below. The lower lip usually catches the light, so "
                "keep it paler than the upper one.",
    },
    "ears": {
        "pencil": "HB",
        "technique": "Check the height against the guide: the ear runs from roughly the brow line "
                     "down to the base of the nose.",
        "text": "Draw the outer rim as one curve, then the inner fold inside it. Keep the detail "
                "low. An ear drawn too carefully pulls attention away from the eyes, which is "
                "where you want it.",
    },
    "contour": {
        "pencil": "HB, 2B along the shadowed side",
        "technique": "Press harder on the side the light is coming from least. A line of even "
                     "weight all the way round flattens the face.",
        "text": "Draw the jaw from the ear down to the chin, checking it against the oval. Then "
                "the hairline, which is a soft transition rather than an edge: let it break up "
                "instead of closing it into a hard band across the forehead.",
    },
    "outline": {
        "pencil": "2B",
        "technique": "Draw hair as a few large masses, not as individual strands. Strands come "
                     "last, if at all, and only at the edges.",
        "text": "Complete the outside shape of the hair and the shoulders. Then go back over the "
                "lines you want to keep, and erase the construction lines from the first step. "
                "This is the point where it stops looking like a diagram.",
    },
    "values": {
        "pencil": "HB for light tones, 2B for mid, 4B for the darks",
        "technique": "Squint hard at the reference until the detail disappears and only patches "
                     "of light and dark remain. Those patches are what you are drawing.",
        "text": "Fill each area as one flat tone, with no blending yet, and leave the lightest "
                "areas as bare paper. Work from light to dark: it is easy to deepen a tone and "
                "difficult to lift one out.",
    },

    # ---- objects --------------------------------------------------------------------
    "proportion": {
        "pencil": "2H, or an HB held lightly",
        "technique": "Hold your pencil at arm's length, thumb marking the width, and compare it "
                     "against the height. The ratio printed on the guide is the one to match.",
        "text": "Draw the box the object sits inside, then the centre lines across it. Block the "
                "object in as straight lines and simple shapes. Anything round gets its full "
                "ellipse now, even the half you cannot see, so it sits straight later.",
    },
    "silhouette": {
        "pencil": "HB",
        "technique": "Check the shape by looking at the gaps around the object rather than the "
                     "object itself. Errors are far easier to spot in the negative space.",
        "text": "Draw the outer edge in one continuous pass, keeping it light. Follow the big "
                "turns only and resist adding detail. If the outline is wrong, nothing drawn "
                "inside it will rescue the drawing.",
    },
    "contours": {
        "pencil": "HB, 2B for edges nearest you",
        "technique": "Let the line change weight as it travels: heavier where the form turns away "
                     "or where one part overlaps another, lighter across flat areas.",
        "text": "Add the edges inside the silhouette: where surfaces meet, where parts overlap, "
                "and the openings. Keep ellipses symmetrical. A lopsided rim is the fastest way "
                "to make a cup look broken.",
    },

    # ---- hands ----------------------------------------------------------------------
    "hand_block": {
        "pencil": "2H, or an HB held almost flat",
        "technique": "Draw the palm as one flat slab, not as an outline with fingers stuck on. "
                     "Everything else hangs off this shape, so get its tilt right before "
                     "anything else.",
        "text": "Block the palm in as a four-sided shape, slightly wider across the knuckles "
                "than at the wrist. Mark the circle inside it -- that is the fleshy mass of the "
                "palm and it tells you the scale of everything else. Draw the wrist axis out of "
                "the bottom. Then put one straight line down the middle of each finger, from the "
                "knuckle arc outwards. Lines only at this stage: no outlines, no nails.",
    },
    "hand_joints": {
        "pencil": "HB, still light",
        "technique": "The knuckles do not sit on a straight line. They arc, and the arc flattens "
                     "or deepens as the hand turns -- which is most of what tells the viewer "
                     "what angle they are looking from.",
        "text": "Draw the knuckle arc across the finger bases, following the curve in the guide "
                "rather than a straight row. Then mark the two joints on each finger. They are "
                "not evenly spaced: the segment nearest the palm is the longest, the middle one "
                "about two thirds of it, the tip segment shortest. The thumb is the exception "
                "with only two segments, and it joins the palm much lower down than the fingers.",
    },
    "hand_volumes": {
        "pencil": "HB",
        "technique": "Think of each segment as a box or a short cylinder, not a flat strip. "
                     "Fingers taper: each segment is narrower than the one before it.",
        "text": "Give every segment width, working out from the axis you drew. Keep the far side "
                "of each joint slightly narrower than the near side. Where one finger passes in "
                "front of another, draw the near one complete and let the far one disappear "
                "behind it -- that overlap is what creates depth in a hand.",
    },
    "hand_outline": {
        "pencil": "2B for the outline, HB for the creases",
        "technique": "Follow the construction rather than the photo. If the outline and the "
                     "block-in disagree, the block-in is usually right and your eye is being "
                     "fooled by foreshortening.",
        "text": "Draw the real edge over your construction, rounding the knuckles and letting "
                "the webbing between the fingers rise about a third of the way up the first "
                "segment -- fingers do not separate at the knuckle. Add the creases at each "
                "joint as short, light lines. Then erase the construction. Nails sit on the top "
                "plane of the last segment and are flatter than they look.",
    },

    # ---- figures ---------------------------------------------------------------------
    "body_hatch": {
        "pencil": "A sharp 2B",
        "technique": "Now turn the flat tones into strokes. Pick a direction for each part "
                     "of the body before you start: around the form, not across it.",
        "text": "Take the value blocks you just laid in and build them from hatching that "
                "curves around each limb. One layer in the mid-tones, two where it is "
                "darker, three or four in the deepest shadow -- same spacing and weight "
                "as the hatching in the other modes, just following the body. This is the "
                "step most people skip, and it is the one that makes the difference "
                "between tone that sits flat on the paper and tone that describes a body.",
    },
    "body_action": {
        "pencil": "2B held loosely, or a stick of charcoal on its side",
        "technique": "Draw from the shoulder, not the wrist, and do it in one pass. Give "
                     "yourself thirty seconds and no eraser: the point is to catch the "
                     "rhythm of the pose before your eye starts negotiating with it.",
        "text": "One long curve, from the head down through the chest and pelvis and on "
                "toward whichever foot carries the weight. Follow the bend of the whole "
                "figure rather than its outline. If the line is straight you have almost "
                "certainly missed the pose -- almost nobody stands symmetrically, and that "
                "slight curve is the difference between a figure and a mannequin.",
    },
    "body_tilts": {
        "pencil": "2B, still light",
        "technique": "Two bars, one across the shoulders and one across the hips. Compare "
                     "their angles against each other, not against the edge of the paper.",
        "text": "In any pose with the weight on one leg those two bars tilt in opposite "
                "directions: the hip of the weighted leg rides up, and the shoulder above "
                "it drops. That opposition is contrapposto, and getting it is the single "
                "biggest step from a stiff drawing to a living one. Mark the plumb line "
                "down from the chest too -- it should land near the supporting foot.",
    },
    "body_masses": {
        "pencil": "HB for the boxes, 2B for the head",
        "technique": "Two solid masses on a flexible spine: the ribcage and the pelvis. "
                     "Everything else hangs off them, and the torso's whole movement is "
                     "those two blocks tilting and twisting against each other.",
        "text": "Block the ribcage in as a rounded box sitting on the shoulder bar, and "
                "the pelvis as a smaller box on the hip bar. Add the head as an egg, "
                "tilted with the neck rather than sitting straight on it. Check the whole "
                "figure against the head: an adult standing upright runs about seven and a "
                "half heads, and the ruler on the guide shows what this pose measures.",
    },
    "body_limbs": {
        "pencil": "HB",
        "technique": "Limbs are tapering cylinders, not tubes. Each segment narrows toward "
                     "the joint below, and foreshortening shortens a limb pointing toward "
                     "you without making it any thinner.",
        "text": "Run a line down each limb through its joints, then give the segments "
                "width. Upper arm into forearm, thigh into calf, each a little narrower "
                "than the last. Where a limb crosses in front of the body, draw the near "
                "one complete and let the far one disappear behind it. Hands and feet stay "
                "as simple wedges at this scale -- they have their own modes in this app, "
                "and detailing them here only pulls attention off the pose.",
    },
    "body_outline": {
        "pencil": "2B for the contour, HB inside",
        "technique": "Follow the construction rather than the photograph. Where the two "
                     "disagree it is usually the construction that is right and your eye "
                     "that is being fooled by a fold of clothing.",
        "text": "Draw the real edge over the block-in, letting the line swell where the "
                "form turns toward you and thin where it turns away. Keep the drapery "
                "subordinate to the body underneath -- clothing follows the figure, and a "
                "fold drawn without knowing what is beneath it reads as a crease in paper. "
                "Then erase the scaffolding.",
    },
}

# `finish` depends on the style family you chose, so it gets its own table
FINISH = {
    "line": {
        "pencil": "2B, kept sharp",
        "technique": "One confident stroke beats four tentative ones. Draw from the shoulder for "
                     "long lines, from the fingers only for short detail.",
        "text": "Go over the drawing with your final line weight and erase everything underneath. "
                "There is no shading in this style, so the line itself has to carry the form: "
                "vary its thickness instead of adding tone.",
    },
    "construct": {
        "pencil": "2H for guides, HB for structure, 2B for accents; a ruler helps",
        "technique": "Keep hatching in one consistent direction per surface, and keep the spacing "
                     "even. Irregular spacing reads as texture, not shadow.",
        "text": "Firm up the construction into finished edges, then lay light diagonal hatching "
                "into the shadow areas only. Darken the key edges last and erase any guides you "
                "no longer need.",
    },
    "value": {
        "pencil": "HB, 2B, 4B and 6B; a blending stump is optional",
        "technique": "Keep each tone flat and distinct. If two neighbouring tones look the same, "
                     "the study has failed at its one job.",
        "text": "Work through the tones from light to dark, leaving the brightest shapes as bare "
                "paper. Hold the edges between tones crisp: this style is about seeing the big "
                "shapes of light, not about smooth gradients.",
    },
    "hatch": {
        "pencil": "A sharp HB or 2B, or a fine liner; re-sharpen often",
        "technique": "Build darkness with more layers, never more pressure. Each new layer crosses "
                     "the one beneath at roughly 30 to 45 degrees.",
        "text": "Lay the first layer of parallel strokes across every shaded area. Add a second "
                "crossing layer only where it is darker, a third darker still. On curved surfaces "
                "let the strokes follow the curve. Leave the highlights as untouched paper.",
    },
    "real": {
        "pencil": "2H through 6B, with a blending stump and a kneaded eraser",
        "technique": "Build tone in thin layers using small overlapping circles. Press hard only "
                     "in the very darkest accents, and blend along the form rather than across it.",
        "text": "Lay the mid-tones first and blend them smooth, then deepen the shadows gradually. "
                "Lift the highlights back out with a kneaded eraser rather than drawing around "
                "them. Add texture and the sharpest details last.",
    },
}

# Where one subject's finishing advice genuinely differs from its family's.
FINISH_OVERRIDE = {
    "body_formhatch": {
        "pencil": "A sharp 2B or a fine liner",
        "technique": "Strokes that wrap the form. A line drawn straight across an arm "
                     "flattens it; the same line curved around it makes a cylinder. That "
                     "is the whole trick, and it is the step between a flat value study "
                     "and a drawing that looks solid.",
        "text": "Work limb by limb, laying bands of strokes around each one as though you "
                "were wrapping it. Cross them with a second layer running along the limb "
                "where it is darker, then a diagonal third, and a fourth only in the "
                "deepest shadow -- the same four layers as the Cross-Hatch in the other "
                "modes, just curved to the body instead of straight. Keep the strokes "
                "visible: this style is a record of how the tone was built, and a "
                "beginner learns more from being able to count the layers than from a "
                "smooth finish.",
    },
    "body_gesture": {
        "pencil": "2B or charcoal, held loosely",
        "technique": "Speed is the method, not a shortcut. A gesture drawing is finished "
                     "when the pose reads, which is usually well before it looks like a "
                     "picture.",
        "text": "Strengthen the line of action and let everything else stay as it fell. "
                "Resist tidying: the value of this drawing is that it records what you saw "
                "in the first few seconds. If you want twenty of these rather than one "
                "careful drawing, you are using it correctly.",
    },
    "body_mannequin": {
        "pencil": "2H for the scaffolding, HB for the masses, 2B for the bars",
        "technique": "Keep it readable as construction. This is a working diagram of how "
                     "the figure is put together, so clarity beats finish.",
        "text": "Firm up the ribcage and pelvis, the head egg and the limb volumes, and "
                "leave the shoulder and hip bars showing. Check the proportion in heads one "
                "last time, and check that the plumb line from the chest still lands near "
                "the supporting foot -- if it does not, the figure will look like it is "
                "falling over, however well the parts are drawn.",
    },
    "hand_construct": {
        "pencil": "2H for the block-in, HB for structure, 2B for the joint creases",
        "technique": "Keep the construction visible and readable. A construction drawing is for "
                     "working out the hand's angle and proportion, so clarity beats prettiness.",
        "text": "Firm up the palm slab and the finger boxes into clean edges, and mark each joint "
                "clearly. Compare the length of the whole hand against the palm alone -- they are "
                "close to equal on most hands, and that single check catches most of the errors "
                "beginners make. Leave the axes in; they are the point of this style.",
    },
    "hand_realistic": {
        "pencil": "2H through 6B, blending stump, kneaded eraser",
        "technique": "Skin over bone: the knuckles and the back of the hand have hard forms just "
                     "under the surface, while the palm and the finger pads are soft. Blend the "
                     "soft parts, keep the bony ones crisp.",
        "text": "Lay the mid-tones and blend along the length of each finger, never across it. "
                "Deepen the shadow between the fingers and under the palm, which are the darkest "
                "notes in the whole drawing. Lift highlights off the knuckles and the nail plates "
                "last. Draw skin creases as tone, not line.",
    },
}

ACCENT = "a66a00"


def step_markup(stage_key, style_key):
    """Kivy markup for one stage: pencil, technique, then what to do."""
    if stage_key == "finish":
        from ..core.styles import ALL
        d = FINISH_OVERRIDE.get(style_key) or FINISH.get(ALL[style_key].family) or FINISH["real"]
    else:
        d = STEPS.get(stage_key)
    if d is None:
        return ""
    h = lambda t: f"[b][color={ACCENT}]{t}[/color][/b]"
    return (f"{h('Pencil')}\n{d['pencil']}\n\n"
            f"{h('Technique')}\n{d['technique']}\n\n"
            f"{h('What to do')}\n{d['text']}")
