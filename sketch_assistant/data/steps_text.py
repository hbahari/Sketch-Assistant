"""Per-stage instructions: which pencil, which technique, what to actually do.

Keyed by the stage ids produced in core/steps.py, so the words and the picture can never
drift apart. `finish` is the one stage whose advice depends on the chosen style, so it has
its own table.
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
}

# `finish` depends on the style you chose, so it gets its own table
FINISH = {
    "line_art": {
        "pencil": "2B, kept sharp",
        "technique": "One confident stroke beats four tentative ones. Draw from the shoulder for "
                     "long lines, from the fingers only for short detail.",
        "text": "Go over the drawing with your final line weight and erase everything underneath. "
                "There is no shading in this style, so the line itself has to carry the form: "
                "vary its thickness instead of adding tone.",
    },
    "technical": {
        "pencil": "2H for guides, HB for structure, 2B for accents; a ruler helps",
        "technique": "Keep hatching in one consistent direction per surface, and keep the spacing "
                     "even. Irregular spacing reads as texture, not shadow.",
        "text": "Firm up the construction into finished edges, then lay light diagonal hatching "
                "into the shadow areas only. Darken the key edges last and erase any guides you "
                "no longer need.",
    },
    "value_study": {
        "pencil": "HB, 2B, 4B and 6B; a blending stump is optional",
        "technique": "Keep each tone flat and distinct. If two neighbouring tones look the same, "
                     "the study has failed at its one job.",
        "text": "Work through the tones from light to dark, leaving the brightest shapes as bare "
                "paper. Hold the edges between tones crisp: this style is about seeing the big "
                "shapes of light, not about smooth gradients.",
    },
    "crosshatch": {
        "pencil": "A sharp HB or 2B, or a fine liner; re-sharpen often",
        "technique": "Build darkness with more layers, never more pressure. Each new layer crosses "
                     "the one beneath at roughly 30 to 45 degrees.",
        "text": "Lay the first layer of parallel strokes across every shaded area. Add a second "
                "crossing layer only where it is darker, a third darker still. On curved surfaces "
                "let the strokes follow the curve. Leave the highlights as untouched paper.",
    },
    "photoreal": {
        "pencil": "2H through 6B, with a blending stump and a kneaded eraser",
        "technique": "Build tone in thin layers using small overlapping circles. Press hard only "
                     "in the very darkest accents, and blend along the form rather than across it.",
        "text": "Lay the mid-tones first and blend them smooth, then deepen the shadows gradually. "
                "Lift the highlights back out with a kneaded eraser rather than drawing around "
                "them. Add texture and the sharpest details last.",
    },
}
FINISH["obj_contour"] = FINISH["line_art"]
FINISH["obj_shapes"] = FINISH["technical"]
FINISH["obj_value"] = FINISH["value_study"]
FINISH["obj_hatch"] = FINISH["crosshatch"]
FINISH["obj_realistic"] = FINISH["photoreal"]

ACCENT = "a66a00"


def step_markup(stage_key, style_key):
    """Kivy markup for one stage: pencil, technique, then what to do."""
    d = FINISH.get(style_key, FINISH["photoreal"]) if stage_key == "finish" else STEPS.get(stage_key)
    if d is None:
        return ""
    h = lambda t: f"[b][color={ACCENT}]{t}[/color][/b]"
    return (f"{h('Pencil')}\n{d['pencil']}\n\n"
            f"{h('Technique')}\n{d['technique']}\n\n"
            f"{h('What to do')}\n{d['text']}")
