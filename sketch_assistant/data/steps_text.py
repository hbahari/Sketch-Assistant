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
        "pencil": "Paper, then HB, 2B and 4B -- the key under the picture says which grey is which",
        "technique": "Value just means how light or dark something is, whatever its colour. "
                     "This picture keeps only a few greys, so the big light and dark shapes "
                     "show before any detail gets in the way. Squint at the photo and you will "
                     "see the same shapes.",
        "text": "Draw the borders between the greys lightly, as if they were the outlines of "
                "countries on a map. Leave the lightest shapes as bare paper. Then fill every "
                "shape of the next grey with one flat, even layer of the pencil the key gives "
                "it, and so on down to the darkest. No blending and no detail yet. Work from "
                "light to dark: a tone is easy to deepen and hard to lift out. When you have "
                "finished, the drawing should already read as the subject from across the "
                "room -- if it does not, the values are wrong, and no amount of detail later "
                "will fix that.",
    },
    # ---- the bridge from hatching to a realistic finish, shared by every mode -----------
    "hatch_tone": {
        "pencil": "A sharp HB or 2B",
        "technique": "The same values as the step before, built from strokes instead of flat "
                     "fills. Darker means more crossing layers, never more pressure.",
        "text": "Lay one layer of parallel strokes over everything except the lightest shapes, "
                "a second crossing layer over the darker ones, and more layers only in the "
                "darkest. Keep the strokes light and close together: they are going to be "
                "blended in the next step, and heavy, widely spaced strokes leave stripes that "
                "will not blend out.",
    },
    "hatch_blend": {
        "pencil": "A blending stump (tortillon) for small areas, a tissue or chamois for large ones",
        "technique": "Blend along the form and from dark into light, with light pressure. Keep "
                     "a clean stump for the light areas: one that has been in the darks will "
                     "grey everything it touches. Never scrub -- it polishes the paper, and "
                     "polished paper will not take more graphite.",
        "text": "Go over the hatching until the strokes melt into continuous tone. The lines of "
                "your drawing should still be there; blending moves graphite around, it does "
                "not erase anything. Stay out of the lightest shapes altogether. The result is "
                "softer and a little flat -- that is right, the next step brings back the "
                "contrast. If the strokes will not disappear, they were spaced too widely: "
                "add a light layer in between and blend again.",
    },
    "lights_darks": {
        "pencil": "Kneaded eraser, pinched to an edge; 4B to 6B for the darks",
        "technique": "Blue outlines: the brightest shapes -- keep them as clean paper, or lift "
                     "them back out with the eraser, pressing and lifting rather than rubbing. "
                     "Red outlines: the darkest shapes -- press to full dark, in small strokes.",
        "text": "This is where shading turns into light and shadow. Light falls on a form in a "
                "few distinct ways, and each is drawn differently:\n"
                "- [b]Highlight[/b]: where light hits directly. Bare paper. Hard-edged on shiny "
                "things (an eye, glass), soft on skin and cloth.\n"
                "- [b]Light side[/b]: the lit surface, getting slowly darker as it turns away from "
                "the light.\n"
                "- [b]Core shadow[/b]: the darkest band of the shadow side, just past where light "
                "turns to shadow. Soft-edged on round forms, sharp on angular ones.\n"
                "- [b]Reflected light[/b]: a slightly lighter area inside a shadow, from light "
                "bouncing off something nearby. Lift it a touch -- it must stay darker than "
                "anything on the lit side.\n"
                "- [b]Cast shadow[/b]: the shadow a form throws onto something else. Darkest and "
                "sharpest where the two touch, softer and lighter further away.\n"
                "- [b]Contact shadow[/b]: the thin, darkest accent where two surfaces meet -- "
                "mouth corners, between fingers, under an object. Most red outlines are these.\n"
                "Do the marked shapes first, then look for the rest of each kind in the photo.",
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
    # ---- eyes -----------------------------------------------------------------------
    "eye_envelope": {
        "pencil": "2H, barely touching the paper",
        "technique": "Measure with the pencil: hold it at arm's length against the photo, mark "
                     "the eye's width with your thumb, and see how many times the height goes "
                     "into it. Then check the tilt the same way before drawing anything.",
        "text": "Put down four dots and one line, and nothing else: a dot at each corner, one "
                "at the highest point of the upper lid and one at the lowest point of the lower "
                "lid, then the line from corner to corner. That line is almost never level -- "
                "one corner sits higher than the other -- and getting its slope right now is "
                "what stops the finished eye looking like a symbol of an eye. Notice that the "
                "high point of the upper lid and the low point of the lower lid are not above "
                "one another.",
    },
    "eye_ball": {
        "pencil": "2H for the ball, HB for the lids",
        "technique": "Draw through. The eyeball is a sphere sitting in a socket and the lids are "
                     "two strips of skin wrapped over it, so draw the whole ball first, even "
                     "though most of it will never show.",
        "text": "Lightly draw the ball as a full circle, bigger than you expect: about twice "
                "the width of the iris. Then lay the upper lid over it as one curve from corner "
                "to corner through your high dot, and the lower lid through your low dot. The "
                "upper lid is the more arched of the two; the lower is nearly flat for most of "
                "its length. Because the lids lie on a ball, they bulge toward you in the "
                "middle -- keep that in mind when you shade later.",
    },
    "eye_lids": {
        "pencil": "HB",
        "technique": "The iris is a full circle that the lids cut into. Draw the whole circle "
                     "first and let the lids hide part of it, rather than drawing the visible "
                     "piece as its own shape.",
        "text": "Draw the iris as a complete circle, then erase what the upper lid covers -- on "
                "a relaxed eye the lid hides the top of it, and the lower lid just touches the "
                "bottom. An iris showing white all the way round reads as fright. Put the pupil "
                "dead centre of the iris, not centre of the visible part. Then give the lower "
                "lid its thickness: a second line just inside the first, which is the wet rim "
                "the lashes grow out of. Add the crease above the upper lid if there is one, "
                "following the lid but drifting away from it toward the middle.",
    },
    "eye_plan": {
        "pencil": "HB, very lightly -- these are notes to yourself",
        "technique": "Decide where the white is before you add any dark. Graphite cannot be "
                     "made lighter than the paper, so the highlight has to be saved, not added.",
        "text": "Outline the highlight in the iris and promise yourself not to shade inside it. "
                "Mark the band of shadow the upper lid throws across the top of the iris -- it "
                "is why the top of an iris is always darker than the bottom, and leaving it out "
                "makes the eye look like it is staring. Finally note which way the lashes grow: "
                "they fan outward, leaning toward whichever corner they are nearer, and the "
                "lower ones are shorter and fewer. Do not draw any lashes yet.",
    },
    "eye_outline": {
        "pencil": "HB, then 2B along the upper lid",
        "technique": "Line weight carries the form. The upper lid line is the heaviest because "
                     "the lashes and their shadow sit on it; the lower lid is light enough to "
                     "almost disappear toward the inner corner.",
        "text": "Go over the lids with their real shapes, using your construction as the guide "
                "and the photo for the small departures from it. Thicken the upper lid line "
                "and let it taper at both ends. Draw the lower lid broken and light. At the "
                "inner corner draw the small pink fold of the tear duct instead of bringing the "
                "two lids to a sharp point -- it is the detail most often left out. Firm up "
                "the iris and the pupil, and the crease.",
    },
    "eye_surround": {
        "pencil": "HB",
        "technique": "Draw the brow as a shape first and as hairs never, at this stage. An eye "
                     "without what surrounds it floats on the page.",
        "text": "Place the brow, measuring its distance from the lid in iris-heights. Block it "
                "in as one tapered shape: thickest toward the nose, thinning as it arcs over "
                "and down past the outer corner. Add the fold below the lower lid and any "
                "lines at the outer corner, lightly. Then erase the construction -- the ball, "
                "the box and the axis have done their job.",
    },
    "eye_blend": {
        "pencil": "2B on its side, then a blending stump or tissue",
        "technique": "Blend from the dark into the light, never the other way, and keep the "
                     "stump off the highlight. Blending is for joining tones, not for creating "
                     "them: lay the right value first, then soften the edge.",
        "text": "Turn your flat value blocks into continuous tone. Soften every boundary "
                "between them so one value slides into the next. The white of the eye is not "
                "white: it is a ball, so it darkens toward both corners and under the upper "
                "lid, and only the patch nearest the light is left as bare paper. At this "
                "stage nothing should be sharp -- no lashes, no iris pattern. If it looks like "
                "the photo slightly out of focus, it is right.",
    },
    "eye_iris_tone": {
        "pencil": "4B for the pupil and the rim, 2B and a sharp HB for the fibres, kneaded eraser",
        "technique": "Work from the pupil outwards in short strokes, like spokes. The iris is a "
                     "shallow bowl with a pattern in it, not a flat disc with lines on it.",
        "text": "Fill the pupil as dark as your pencil will go, leaving the highlight clean. "
                "Darken the outer rim of the iris -- most irises have a darker ring at the "
                "edge. Then draw the fibres: short strokes radiating from the pupil, uneven in "
                "length and weight, with a second set coming inward from the rim to meet them. "
                "Keep the top of the iris darker, under the lid's shadow, and let the side "
                "opposite the highlight glow a little lighter: light passes through the iris "
                "and brightens the far side. Pinch the eraser to a point to lift a few pale "
                "fibres back out.",
    },
    "eye_form": {
        "pencil": "HB and 2B, stump",
        "technique": "Shade the lids as bands wrapping a ball. The value changes along the lid "
                     "as it turns away from the light, not just from top to bottom.",
        "text": "Model the upper lid: darkest in the crease, lighter on the swell below it, "
                "dark again where it meets the lashes. Give the lower lid its lit rim -- that "
                "thin wet edge catches light and is usually the second-brightest thing in the "
                "drawing. Deepen the two corners, shade the tear duct softly, and put the "
                "shadow under the lower lid in. Sharpen the edges that are really sharp (lid "
                "against eyeball) and leave the rest soft.",
    },
    "eye_lashes": {
        "pencil": "A sharp 2B or 4B",
        "technique": "Flick, do not draw. Start each lash at the lid with pressure and lift off "
                     "as you go, so it is thick at the root and vanishes at the tip. Turn the "
                     "paper so the stroke curves the natural way for your hand.",
        "text": "Lashes go on last and there are fewer than you think. Draw them in clumps of "
                "two or three whose tips touch, curving up and away, leaning toward the nearer "
                "corner. Upper lashes are long and start from the lid's outer edge; lower ones "
                "are short, sparse and start from the far side of the wet rim, not from the "
                "eyeball. Let a few upper lashes cross the highlight and reflect in it. Then "
                "the brow: short hairs laid in its direction of growth, upward near the nose "
                "and flattening outward, over the shape you blocked in.",
    },
    # ---- noses ----------------------------------------------------------------------
    "nose_envelope": {
        "pencil": "2H, barely touching the paper",
        "technique": "Measure before drawing. A nose is usually about as wide as the gap between "
                     "the inner corners of the eyes, and from its root between the eyes to its "
                     "base it is about a third of the face: the same as from the brows to the "
                     "hairline, or from the base of the nose to the chin. Check both against the "
                     "photo with your pencil held at arm's length.",
        "text": "Mark three things and nothing else: the root of the nose between the eyes, the "
                "base where the nostrils are, and the width across the wings. Draw a light box "
                "through them and a centre line from root to base. The centre line follows the "
                "tilt of the face; if the head is turned, the whole nose shifts toward the far "
                "side, so line it up with the photo rather than with the middle of the box.",
    },
    "nose_wedge": {
        "pencil": "2H",
        "technique": "Think of the nose as a wedge of flat planes stuck onto the face: a narrow "
                     "front plane down the bridge, a side plane on each side, and a base plane "
                     "underneath where the nostrils are. Light falls differently on each plane, "
                     "and those differences are what you will shade later.",
        "text": "Draw the front plane as a long, narrow strip from the root to the tip, wider at "
                "the tip. Join its edges out to the wings for the two side planes. Then draw the "
                "base plane as a flat shape underneath, between the wings. The base plane is the "
                "one most people forget: it faces down, so it is nearly always in shadow, and "
                "without it the nose looks pasted on.",
    },
    "nose_balls": {
        "pencil": "HB, lightly",
        "technique": "The three-ball method: one ball for the fleshy tip, a smaller ball on each "
                     "side for the wings. The nostrils sit under and inside the wings, not on the "
                     "front of the nose.",
        "text": "Draw a circle for the ball of the tip and a smaller one for each wing, resting "
                "on the base line and just overlapping the tip. Place each nostril under its "
                "wing as a small comma or kidney shape, angled toward the centre. Between them "
                "is the columella, the strip of skin under the tip. From the front only part of "
                "each nostril shows -- draw just the part you can see in the photo.",
    },
    "nose_plan": {
        "pencil": "HB, very lightly -- these are notes to yourself",
        "technique": "A nose is drawn mostly with tone, not lines, so plan the shadow shapes "
                     "before any shading. The light direction decides all of them.",
        "text": "Lightly outline the side plane facing away from the light, the base plane "
                "underneath, and the shadow the nose throws onto the upper lip, on the side away "
                "from the light. Mark the two highlights you will keep white: the strip down the "
                "bridge and the spot on the tip. Note where the darkest accents go, deep inside "
                "the nostrils. The app guesses the light from the photo and shades the side it "
                "thinks is in shadow; check that against the photo.",
    },
    "nose_outline": {
        "pencil": "HB, then 2B for the nostrils",
        "technique": "Only a few lines on a nose are real lines: the nostril openings and the "
                     "creases round the wings. The sides of the bridge have no outline at all -- "
                     "they are a change of tone.",
        "text": "Draw the nostrils, darkest at their inner, upper part and softer toward the "
                "outside. Draw the crease where each wing meets the cheek, firm at the bottom "
                "and fading as it rises. Resist drawing lines down the sides of the bridge; if "
                "you need a reminder of where the side plane turns, make a mark so faint it will "
                "disappear under the shading.",
    },
    "nose_surround": {
        "pencil": "HB",
        "technique": "A nose only reads as a nose with something around it. Draw the "
                     "surroundings lightly, so they place the nose without competing with it.",
        "text": "Place the inner corners of the eyes, the brows and the line of each cheek, and "
                "the top of the upper lip with the groove that runs up to the nose. Then erase "
                "the construction, keeping only the faintest trace of the planes to guide the "
                "shading.",
    },
    "nose_planes": {
        "pencil": "HB and 2B, blending stump",
        "technique": "Shade plane by plane. The front plane is lit; the side plane away from the "
                     "light is the darkest of the upper planes; the turn between them is soft "
                     "over the fleshy tip and sharper over the bony bridge.",
        "text": "Lay tone on the shadow side plane and soften it where it turns toward the "
                "front. Keep the bridge strip light; it changes where the bone gives way to "
                "cartilage, about halfway down, often a slight bump or a change in the width of "
                "the highlight. Add the soft shadow at the root, where the nose meets the brow "
                "and the corners of the eyes, and darken the side where the nose meets the "
                "cheek.",
    },
    "nose_base": {
        "pencil": "2B to 4B, kneaded eraser",
        "technique": "The base plane and the cast shadow are what fix a nose to the face. Without "
                     "them it floats.",
        "text": "Shade the base plane under the tip, darker than the side planes. Fill the "
                "nostrils, darkest deep inside; their edges are not pure black, because they "
                "catch light bouncing up from the lip. Lift a touch of that reflected light on "
                "the underside of the wings and the columella. Then draw the cast shadow on the "
                "upper lip: darkest and sharpest right under the nose, softer and lighter as it "
                "spreads away.",
    },
    # ---- caricature -----------------------------------------------------------------
    "car_head": {
        "pencil": "HB, held lightly",
        "technique": "Ghosting: swing the hand over each shape before the pencil touches.",
        "text": "Draw the head shape, then the outline of the hair as one simple mass round it. "
                "Add the centre line and the eye, nose and mouth lines. These are the "
                "caricature's proportions -- already pushed -- so copy them as the guide shows "
                "rather than from the photo.",
    },
    "car_features": {
        "pencil": "HB",
        "technique": "Shapes before detail: if an oval is in the wrong place, the finished eye "
                     "will be too.",
        "text": "Draw an oval for each eye on the eye line, a triangle for the nose from between "
                "the eyes down to the nose line, and an oval for the mouth. Keep them light.",
    },
    "car_outline": {
        "pencil": "2B or a fine liner",
        "technique": "One even line weight, drawn from the elbow for the long curves. The icon's "
                     "style is clean: a line, not a sketchy cloud of them.",
        "text": "Draw the jaw and chin, then the outline of the hair, including the hairline "
                "across the forehead. Where hair falls over the face, the face's outline stops. "
                "Add the soft curve of the chin just above its outline, and a lighter one under "
                "where the lower lip will be.",
    },
    "car_eyes": {
        "pencil": "2B or a fine liner",
        "technique": "The upper lid is the heaviest line of the face; the lower one lighter and "
                     "shorter.",
        "text": "The eyes carry the expression, so this is the step to take slowly. Draw the "
                "iris, a big dark pupil with a white catchlight left as paper, and a few short "
                "lines from the pupil out. Then the heavy upper lid over it (the lids cover the "
                "top and bottom of the iris), the crease above, and the lower lid lighter. Sweep "
                "the lashes out from the outer half, longest at the corner. For the brows, a "
                "light tapered shape, then short hair strokes leaning from the inner end out.",
    },
    "car_nose_mouth": {
        "pencil": "2B or a fine liner",
        "technique": "Curves, not dots: a nose drawn as two dots looks like a mask.",
        "text": "Draw a round curl for each nostril wing, from above the wing, out and down into "
                "the nostril, a soft curve under the tip between them, and one line down the "
                "side of the nose away from the light. For the mouth, draw the top edge of the "
                "upper lip with its two peaks, the line between the lips heavier, with a small "
                "tick at each corner, and the lower lip. Then the two short ridges from the nose "
                "down to the peaks, and a few light strokes across the lower lip for its fullness. "
                "Last, the laugh lines from beside each nostril down towards the corners of the "
                "mouth, bowing out over the cheek and stopping short of the mouth, and a short "
                "curve under each eye's outer corner for the cheekbone. Keep these light; press "
                "harder only where the photo shows a deep fold.",
    },
    "car_strands": {
        "pencil": "A sharp 2B or a fine liner, lighter than the outline",
        "technique": "Long strokes in the direction the hair falls, each one tapering off at both "
                     "ends. A few strands say hair; many say a mess.",
        "text": "Add the strands the picture shows, following the hair's flow from the parting "
                "outwards and down. Then erase the shapes underneath.",
    },
    "car_hatch": {
        "pencil": "HB, sharp",
        "technique": "Short parallel strokes in one direction per patch, evenly spaced, stopping "
                     "short of the outline. One layer only.",
        "text": "Hatch the shadow side of the face and the darkest parts of the hair, where the "
                "picture shows. Keep it light and sparse: the lines carry this drawing, the "
                "hatching only hints at the light.",
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
        "pencil": "The key under the picture: paper for the lightest grey, then one pencil per grey",
        "technique": "Keep each tone flat and distinct. If two neighbouring tones look the same, "
                     "the study has failed at its one job.",
        "text": "A value study is a plan, not a finished picture: it shows only where the light "
                "and dark shapes are. Work through the greys from light to dark, matching each "
                "to its swatch in the key and leaving the lightest as bare paper. Hold the edges "
                "between tones crisp. Artists make one of these before a shaded drawing because "
                "the big shapes of light are what make a drawing read -- get them right here "
                "and every other style is this, with more on top.",
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
                "them. Add texture and the sharpest details last. If smooth shading feels hard, "
                "take the route the steps show: hatch the tones in, blend the hatching, then "
                "lift the lights and deepen the darks -- each of those is easier than shading "
                "smooth from nothing.",
    },
}

# Where one subject's finishing advice genuinely differs from its family's.
FINISH_OVERRIDE = {
    "car_hatch": {
        "pencil": "2B or a fine liner; HB for the hatching",
        "technique": "Erase the shapes before the hatching goes in, so the hatching doesn't "
                     "get smudged.",
        "text": "Check the lines against the picture, erase the construction, and leave it. A "
                "caricature in this style is finished when it reads, and it reads early: more "
                "hatching makes it heavier, not better.",
    },
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
    "eye_construct": {
        "pencil": "2H for the ball and the box, HB for the lids and the iris",
        "technique": "Leave the construction showing. This drawing is for understanding how "
                     "the eye is built, and it is the page to come back to when a finished "
                     "eye looks wrong and you cannot tell why.",
        "text": "Firm up the lids, the iris and the pupil, and keep the ball, the corner line "
                "and the box visible underneath. Check three things against the photo: how "
                "many irises wide the eye is, how much of the iris the upper lid covers, and "
                "whether the pupil really is in the centre of the iris. Most eyes that look "
                "wrong are wrong in one of those three.",
    },
    "eye_realistic": {
        "pencil": "2H through 6B, a sharp HB, stump, kneaded eraser pinched to a point",
        "technique": "Contrast makes an eye look wet. The darkest dark and the cleanest white "
                     "sit side by side at the highlight, and that one hard edge does more than "
                     "any amount of detail.",
        "text": "Bring the pupil and the upper lash line to full dark. Clean the highlight back "
                "to bare paper and give it one crisp edge. Add the small second highlight on "
                "the wet rim of the lower lid and in the tear duct. Put the faintest shadow of "
                "the lashes on the eyeball below the upper lid. Then stop: over-worked lashes "
                "and an iris with every fibre drawn are the two things that most often spoil "
                "an eye that was right ten minutes earlier.",
    },
    "nose_construct": {
        "pencil": "2H for the box and the planes, HB for the balls and nostrils",
        "technique": "Leave the construction showing. This drawing is for understanding how the "
                     "nose is built, and it is the page to come back to when a finished nose "
                     "looks flat or stuck on.",
        "text": "Firm up the balls and the nostrils and keep the planes visible underneath. "
                "Check three things against the photo: the width against the inner corners of "
                "the eyes, that the base plane is there at all, and that the nostrils sit under "
                "the wings rather than on the front. Most noses that look wrong are wrong in one "
                "of those three.",
    },
    "nose_realistic": {
        "pencil": "2H through 6B, blending stump, kneaded eraser",
        "technique": "Edges make a nose. Keep them hard where a nostril meets its wing and where "
                     "the cast shadow starts, and soft everywhere along the bridge and the sides.",
        "text": "Bring the nostrils and the darkest part of the cast shadow to full dark. Lift "
                "the highlight on the tip and the strip down the bridge back to clean paper. "
                "Soften any line left down the sides of the bridge until it is only a change of "
                "tone. Add skin texture lightly -- pores show most round the tip and the wings -- "
                "and stop before the nose gets more detail than the rest of the face around it.",
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
