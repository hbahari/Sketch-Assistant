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
}


def tips_markup(style_key):
    t = TIPS[style_key]
    steps = "\n".join(f"  {i}. {s}" for i, s in enumerate(t["steps"], 1))
    h = lambda x: f"[b][color=a66a00]{x}[/color][/b]"
    text = f"{h('Pencils & grades')}\n{t['pencils']}\n\n{h('Pressure')}\n{t['pressure']}\n\n{h('Steps')}\n{steps}"
    return text
