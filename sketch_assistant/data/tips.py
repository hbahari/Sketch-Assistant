"""Pencil tips and step-by-step guides per style."""

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
}


def tips_markup(style_key):
    t = TIPS[style_key]
    steps = "\n".join(f"  {i}. {s}" for i, s in enumerate(t["steps"], 1))
    h = lambda x: f"[b][color=0f8f82]{x}[/color][/b]"
    return f"{h('Pencils & grades')}\n{t['pencils']}\n\n{h('Pressure')}\n{t['pressure']}\n\n{h('Steps')}\n{steps}"
