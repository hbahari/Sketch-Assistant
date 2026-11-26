"""Caricature mode: a portrait redrawn as a simple, exaggerated line drawing of the head.

What makes a caricature recognisable is not a big head on everyone; it is *this* face's
differences from an average face, pushed further. So the face is measured, not guessed:

1. The face mesh (core/landmarks.py) gives 468 points on the face in 3D.
2. MediaPipe's own average face (core/face_average.py) is fitted to them -- rotated,
   scaled and moved, nothing else -- so it sits in the same pose. What is left over is
   this face's shape: a wider nose, a longer chin, closer-set eyes.
3. That difference is multiplied by the exaggeration slider and added back. Done in 3D,
   so a turned head is not mistaken for a lopsided face.

The drawing is made from the points, not traced from the photo, which is what keeps it as
clean as the app icon: even lines, a few strands of hair, and only the light hatching a
beginner can copy. Hair comes from MediaPipe's person segmentation, less the skin; it
and anything else off the mesh are moved with the face by interpolating the mesh's own
movement. The surroundings are left out: the head only, cut off under the chin.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

from .face_average import CANONICAL

SEG_NAME = "selfie_segmentation.tflite"
STRENGTH = 2.5             # exaggeration at the slider's top; 0 at the bottom
INK = (45, 45, 45)
SOFT = (150, 150, 150)     # construction lines
HATCH = (110, 110, 110)

# MediaPipe face-mesh indices (the standard published contours)
FACE_OUTLINE = (10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
                400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
                54, 103, 67, 109)
EYES = (  # (upper lid, lower lid), corner to corner; the eye on the image's left first
    ((33, 246, 161, 160, 159, 158, 157, 173, 133), (33, 7, 163, 144, 145, 153, 154, 155, 133)),
    ((263, 466, 388, 387, 386, 385, 384, 398, 362), (263, 249, 390, 373, 374, 380, 381, 382, 362)),
)
BROWS = (  # (upper edge, lower edge), outer end to inner
    ((70, 63, 105, 66, 107), (46, 53, 52, 65, 55)),
    ((300, 293, 334, 296, 336), (276, 283, 282, 295, 285)),
)
LIP_TOP = (61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291)
LIP_LINE = (78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308)
LIP_LOWER = (91, 181, 84, 17, 314, 405, 321)
LIP_OUTER_LOWER = (61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291)
# the lower edge of each wing into the nostril: the two small hooks the icon draws
NOSE_WINGS = ((64, 98, 240, 60, 99, 97), (294, 327, 460, 290, 328, 326))
NOSE_ROOT, NOSE_TIP, CHIN, FOREHEAD = 168, 1, 152, 10
CHEEKS = (50, 280, 101, 330, 151)          # skin samples: both cheeks, forehead
BALD_TEXTURE = 0.8        # a scalp is smoother than this fraction of the cheek's texture


# --------------------------------------------------------------------------- models
_seg = []


def _seg_net():
    if not _seg:
        from .landmarks import MODELS
        path = MODELS / SEG_NAME
        net = None
        if path.exists() and hasattr(cv2.dnn, "readNetFromTFLite"):
            try:
                net = cv2.dnn.readNetFromTFLite(str(path))
            except Exception:
                net = None
        _seg.append(net)
    return _seg[0]


def available():
    from . import landmarks
    return landmarks.mesh_available()


def _person_mask(img):
    """Probability that each pixel is the person (hair included), or None without the model.
    The image is letterboxed to the model's square 256 x 256 so the head isn't squashed."""
    net = _seg_net()
    if net is None:
        return None
    H, W = img.shape[:2]
    s = 256 / max(H, W)
    nh, nw = max(1, int(round(H * s))), max(1, int(round(W * s)))
    box = np.zeros((256, 256, 3), np.uint8)
    oy, ox = (256 - nh) // 2, (256 - nw) // 2
    box[oy:oy + nh, ox:ox + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    x = cv2.cvtColor(box, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    net.setInput(x.transpose(2, 0, 1)[None])
    out = net.forward().reshape(256, 256)[oy:oy + nh, ox:ox + nw]
    return cv2.resize(out, (W, H), interpolation=cv2.INTER_LINEAR)


# --------------------------------------------------------------------------- measuring
def _canonical():
    c = np.array(CANONICAL, float)
    return c * np.array([1.0, -1.0, -1.0])      # to image axes: y down, z away from the viewer


def _fit_average(P):
    """The average face moved into this face's pose: s R C + t closest to P (Umeyama)."""
    C = _canonical()
    mp, mc = P.mean(0), C.mean(0)
    X, Y = C - mc, P - mp
    U, S, Vt = np.linalg.svd(Y.T @ X)
    d = np.sign(np.linalg.det(U @ Vt))
    D = np.diag([1.0, 1.0, d])
    R = U @ D @ Vt
    s = float(np.trace(np.diag(S) @ D) / (X ** 2).sum())
    return s * X @ R.T + mp


@dataclass
class Measure:
    """Everything read from the photo, in the photo's pixels; the slider doesn't change it."""
    shape: tuple
    found: bool
    P: np.ndarray = None           # 468 x 3 mesh
    M: np.ndarray = None           # the average face in the same pose
    irises: list = field(default_factory=list)      # (x, y, r) per eye, image-left first
    hair: list = field(default_factory=list)        # hair outline polylines
    strands: list = field(default_factory=list)     # a few strands inside the hair
    shadows: np.ndarray = None     # face shadow mask (uint8)
    hair_dark: np.ndarray = None   # darkest parts of the hair (uint8)
    jaw_visible: np.ndarray = None  # per FACE_OUTLINE point: drawn or under the hair
    face_h: float = 0.0
    light: int = 1                 # +1 light from the image's left, -1 from the right
    folds: tuple = (0.0, 0.0, 0.0, 0.0)   # how deep each laugh line and cheek line is in the photo


_cache = {}


def _key(img):
    return (img.shape, hash(img.tobytes()[::97]))


WORK_SIDE = 720            # measured at this size at most; the phone shouldn't wait on pixels


def measure(img):
    k = _key(img)
    if k in _cache:
        return _cache[k]
    H, W = img.shape[:2]
    s = min(1.0, WORK_SIDE / max(H, W))
    if s < 1.0:
        m = _measure(cv2.resize(img, (int(round(W * s)), int(round(H * s))), interpolation=cv2.INTER_AREA))
        m = _scaled(m, 1.0 / s, (H, W))
    else:
        m = _measure(img)
    _cache[k] = m
    while len(_cache) > 4:
        _cache.pop(next(iter(_cache)))
    return m


def _scaled(m, k, shape):
    """A Measure made on a smaller copy, in the full image's pixels."""
    if not m.found:
        return Measure(shape, False)
    up = lambda mask: None if mask is None else cv2.resize(mask, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return Measure(shape, True, P=m.P * k, M=m.M * k, irises=[(x * k, y * k, r * k) for x, y, r in m.irises],
                   hair=[p * k for p in m.hair], strands=[p * k for p in m.strands], shadows=up(m.shadows),
                   hair_dark=up(m.hair_dark), jaw_visible=m.jaw_visible, face_h=m.face_h * k, light=m.light,
                   folds=m.folds)


def _measure(img):
    from . import landmarks, noses
    H, W = img.shape[:2]
    face = noses.find_face(img) if landmarks.mesh_available() else None
    if face is None:
        return Measure((H, W), False)
    P, flag = landmarks.face_mesh(img, face.eye_mid, face.mouth_mid, with_flag=True, with_z=True)
    if P is None or flag <= 0:
        return Measure((H, W), False)
    m = Measure((H, W), True, P=P, M=_fit_average(P))
    xy = P[:, :2]
    m.face_h = float(np.linalg.norm(xy[FOREHEAD] - xy[CHIN]))
    fh = m.face_h

    # the irises: MediaPipe's iris model, framed by the mesh's eye corners as MediaPipe does
    for n, (upper, lower) in enumerate(EYES):
        a, b = xy[upper[0]], xy[upper[-1]]
        w = float(np.linalg.norm(b - a))
        res = landmarks.iris_landmarks(img, start=(*((a + b) / 2), 2.3 * w), iterations=2, flip=n == 1) \
            if landmarks.iris_available() and w > 6 else None
        if res is not None and 0.15 * w < res["r"] < 0.32 * w:
            m.irises.append((res["iris"][0], res["iris"][1], res["r"]))
        else:                                    # no model, or a doubtful reading
            mid = np.mean([xy[i] for i in upper[1:-1] + lower[1:-1]], 0)
            m.irises.append((float(mid[0]), float(mid[1]), 0.22 * w))

    poly = xy[list(FACE_OUTLINE)].astype(np.int32)
    face_mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(face_mask, [poly], 255)
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (0, 0), max(1.0, fh / 200)), cv2.COLOR_BGR2LAB).astype(np.float32)
    gray = lab[..., 0]

    # which side is lit: the brighter cheek
    lc = gray[int(xy[50][1]), int(np.clip(xy[50][0], 0, W - 1))] if 0 <= int(xy[50][1]) < H else 0
    rc = gray[int(xy[280][1]), int(np.clip(xy[280][0], 0, W - 1))] if 0 <= int(xy[280][1]) < H else 0
    m.light = 1 if lc >= rc else -1

    # skin colour, from small patches on the cheeks and forehead
    samples = []
    for i in CHEEKS:
        x, y = int(xy[i][0]), int(xy[i][1])
        r = max(2, int(fh * 0.025))
        if r <= x < W - r and r <= y < H - r:
            samples.append(lab[y - r:y + r, x - r:x + r].reshape(-1, 3))
    skin = np.zeros((H, W), bool)
    skin_hue = skin
    if samples:
        # only the brighter patches: a cheek in deep shadow is as dark as dark hair, and
        # sampling it made everything "skin". Skin that matters here (ears, neck, a bald
        # forehead) is outside the face, where the light is usually like the lit cheek.
        lum = [float(x[:, 0].mean()) for x in samples]
        smp = np.vstack([x for x, l in zip(samples, lum) if l >= np.median(lum)])
        mu, cov = smp.mean(0), np.cov(smp.T) + np.eye(3) * 4.0
        d = lab.reshape(-1, 3) - mu
        md = np.einsum("ij,jk,ik->i", d, np.linalg.inv(cov), d).reshape(H, W)
        skin = md < 7.0
        # colour alone, any lightness: a bald scalp in a highlight is still skin-coloured
        d2, c2 = d[:, 1:], cov[1:, 1:]
        skin_hue = (np.einsum("ij,jk,ik->i", d2, np.linalg.inv(c2), d2).reshape(H, W) < 6.0)

    # hair: the person, less skin and the face, down to just under the chin
    person = _person_mask(img)
    chin_y = float(xy[CHIN][1])
    cut = int(min(H, chin_y + 0.05 * fh))
    if person is not None:
        head = (person > 0.5)
        head[cut:] = False
        near = cv2.dilate(face_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(fh * 0.9) | 1,) * 2)) > 0
        # Above the eyes, everything of the person beyond the face is hair -- or a bald
        # scalp, whose outline is the head's and wants drawing just the same. Telling skin
        # from hair by colour there failed on blonde and pink hair. Below the eyes the
        # skin is ears and neck, and is left out.
        rows = np.arange(H)[:, None]
        eye_line = float(min(xy[159][1], xy[386][1]))
        not_skin = ~skin | (rows < eye_line)
        hair = head & near & not_skin & ~(cv2.dilate(face_mask, np.ones((3, 3), np.uint8)) > 0)
        hair = hair.astype(np.uint8) * 255
        k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(3, int(fh * 0.02)) | 1,) * 2)
        hair = cv2.morphologyEx(cv2.morphologyEx(hair, cv2.MORPH_OPEN, k3), cv2.MORPH_CLOSE, k3)
        # below the mouth, hair only hangs close beside the face; wider is shoulders
        mouth_y = float((xy[61][1] + xy[291][1]) / 2)
        fx0, fx1 = float(poly[:, 0].min()), float(poly[:, 0].max())
        band = 0.25 * (fx1 - fx0)
        cols = np.arange(W)
        far = (cols < fx0 - band) | (cols > fx1 + band)
        hair[int(max(0, mouth_y)):, far] = 0
        n_cc, lab_cc, stats, _ = cv2.connectedComponentsWithStats(hair)
        keep = np.zeros_like(hair)
        eye_y = float(min(xy[159][1], xy[386][1]))
        for i in range(1, n_cc):
            # hair grows from the scalp: a patch that never reaches eye level is a collar
            if stats[i, cv2.CC_STAT_AREA] > 0.004 * fh * fh and stats[i, cv2.CC_STAT_TOP] < eye_y:
                keep[lab_cc == i] = 255
        hair = cv2.GaussianBlur(keep, (0, 0), max(1.0, fh * 0.01))
        hair = (hair > 127).astype(np.uint8) * 255
        allowed = np.ones((H, W), np.uint8)
        allowed[cut:] = 0
        allowed[int(max(0, mouth_y)):, far] = 0
        # a bald head: what is above the face is mostly skin. Its outline is still the
        # head's, but there is no hairline to draw across the forehead.
        # Colour alone mistook pink hair for a scalp, so a scalp must also be smoother than
        # a cheek: hair has fine texture, skin under a highlight hardly any. On the test
        # photos the two bald heads came out at 0.43 and 0.73 of their cheeks' texture,
        # hair at 0.91 and up -- a narrow margin, set on those same photos.
        top = (hair > 0) & (rows < float(xy[FOREHEAD][1]) + 0.05 * fh)
        bald = False
        if top.sum() > 0.01 * fh * fh and (skin_hue & top).sum() > 0.5 * top.sum():
            fine = np.abs(gray - cv2.GaussianBlur(gray, (0, 0), max(1.0, fh * 0.01)))
            cx_, cy_ = int(xy[50][0]), int(xy[50][1])
            r_ = max(3, int(fh * 0.02))
            cheek = float(fine[max(0, cy_ - r_):cy_ + r_, max(0, cx_ - r_):cx_ + r_].mean()) + 1e-6
            bald = float(fine[top].mean()) < BALD_TEXTURE * cheek
        if bald:
            allowed[cv2.dilate(face_mask, cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (int(fh * 0.06) | 1,) * 2)) > 0] = 0
        m.hair = _outlines(hair, allowed, fh)
        # strands and shading only where it really is hair: not on a bald scalp
        texture = ((hair > 0) & ~skin).astype(np.uint8) * 255
        texture = cv2.morphologyEx(texture, cv2.MORPH_OPEN, k3)
        m.strands = _streamlines(gray, texture, hair, fh)
        hv = gray[texture > 0]
        if hv.size > 50:
            m.hair_dark = ((gray < np.percentile(hv, 30)) & (texture > 0)).astype(np.uint8) * 255
        # The face's outline is drawn only where it really is an edge: below the eyes,
        # wherever it isn't under the hair; above them -- the forehead, where the mesh's
        # outline is only where the mesh stops -- only against the background. Below the
        # mouth always: hair hanging over the chin is rare, a beard over it common, and a
        # caricature without its jaw has lost the shape it is most often about.
        out = []
        c = xy[list(FACE_OUTLINE)].mean(0)
        eye_y = float(min(xy[159][1], xy[386][1]))
        for i in FACE_OUTLINE:
            q = xy[i] + (xy[i] - c) / (np.linalg.norm(xy[i] - c) + 1e-6) * 0.03 * fh
            x, y = int(np.clip(q[0], 0, W - 1)), int(np.clip(q[1], 0, H - 1))
            if xy[i][1] > mouth_y:
                out.append(True)            # the chin is drawn even under a beard
            else:
                out.append(not hair[y, x] and (xy[i][1] > eye_y or person[y, x] < 0.5))
        m.jaw_visible = np.array(out)
    else:
        m.jaw_visible = np.array([True] * len(FACE_OUTLINE))

    # shadows on the face: the darkest fifth, away from the features themselves
    feats = np.zeros((H, W), np.uint8)
    for upper, lower in EYES:
        cv2.fillPoly(feats, [xy[list(upper) + list(lower[::-1])].astype(np.int32)], 255)
    for upper, lower in BROWS:
        cv2.fillPoly(feats, [xy[list(upper) + list(lower[::-1])].astype(np.int32)], 255)
    cv2.fillPoly(feats, [xy[list(LIP_OUTER_LOWER)].astype(np.int32)], 255)
    cv2.fillPoly(feats, [xy[list(LIP_TOP)].astype(np.int32)], 255)
    for wing in NOSE_WINGS:
        cv2.fillPoly(feats, [xy[list(wing) + [NOSE_TIP]].astype(np.int32)], 255)
    feats = cv2.dilate(feats, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(fh * 0.06) | 1,) * 2))
    inner = cv2.erode(face_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(fh * 0.03) | 1,) * 2))
    fv = gray[(inner > 0) & (feats == 0)]
    if fv.size > 100:
        dark = (gray < np.percentile(fv, 20)) & (inner > 0) & (feats == 0)
        dark = cv2.morphologyEx(dark.astype(np.uint8) * 255, cv2.MORPH_OPEN,
                                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(fh * 0.03) | 1,) * 2))
        n_cc, lab_cc, stats, _ = cv2.connectedComponentsWithStats(dark)
        keep = np.zeros_like(dark)
        for i in range(1, n_cc):
            if stats[i, cv2.CC_STAT_AREA] > 0.006 * fh * fh:
                keep[lab_cc == i] = 255
        m.shadows = keep
    # how deep the laugh lines and cheek lines are: how much darker the photo is along each
    # than just beside it, in units of the face's own contrast
    sd = float(gray[inner > 0].std()) + 1e-6 if (inner > 0).any() else 1.0
    depth = []
    for line, out_dir in _fold_paths(xy):
        on = _mean_along(gray, line)
        off = _mean_along(gray, line + out_dir)
        depth.append(float(np.clip((off - on) / sd, 0.0, 1.0)))
    m.folds = tuple(depth)
    return m


def _smooth_closed(c, sigma):
    if len(c) < 5:
        return c
    k = int(3 * sigma) | 1
    ext = np.vstack([c[-k:], c, c[:k]])
    sm = np.c_[cv2.GaussianBlur(ext[:, 0].reshape(-1, 1), (1, 2 * k + 1), sigma).ravel(),
               cv2.GaussianBlur(ext[:, 1].reshape(-1, 1), (1, 2 * k + 1), sigma).ravel()]
    return sm[k:-k]


def _outlines(mask, allowed, fh):
    """The hair mask's outline as open polylines, leaving out the stretches that are only
    the edge of the photo, the cut under the chin or the limit beside the shoulders --
    those are where the drawing stops, not lines on the head."""
    H, W = mask.shape
    pad = np.pad(allowed, 1)                     # the photo's edge counts as a limit too
    room = cv2.distanceTransform(pad, cv2.DIST_L2, 3)[1:-1, 1:-1]
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cs:
        c = c.reshape(-1, 2).astype(float)
        if len(c) < 20:
            continue
        c = _smooth_closed(c, max(1.5, fh * 0.012))
        e = max(3.0, 0.015 * max(H, W))
        ci = np.clip(np.round(c).astype(int), 0, [W - 1, H - 1])
        edge = room[ci[:, 1], ci[:, 0]] < e
        if edge.all():
            continue
        # rotate so the polyline starts at an edge point, then split on edge runs
        if edge.any():
            s = int(np.argmax(edge))
            c, edge = np.roll(c, -s, 0), np.roll(edge, -s)
        run = []
        for p, e in zip(c, edge):
            if e:
                if len(run) > 8:
                    out.append(np.array(run))
                run = []
            else:
                run.append(p)
        if len(run) > 8:
            out.append(np.array(run if edge.any() else run + [run[0]]))
    return [p[::2] for p in out if len(p) > 4]


def _streamlines(gray, texture, hair, fh, n=26):
    """Strands: lines traced along the hair's own direction, the way the icon draws hair as
    a few long flowing strokes. The direction is read from the photo where the hair has
    visible texture (the structure tensor: strands run across the strongest gradient) and
    taken as parallel to the hair's outline where it doesn't."""
    H, W = gray.shape
    if texture.sum() < 0.02 * fh * fh * 255:
        return []
    g = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), max(1.0, fh / 150))
    gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)
    sig = max(2.0, fh * 0.04)
    jxx, jyy, jxy = (cv2.GaussianBlur(a, (0, 0), sig) for a in (gx * gx, gy * gy, gx * gy))
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2          # along the strands
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / (jxx + jyy + 1e-6)
    # outline-parallel direction from the distance to the hair's edge
    dist = cv2.distanceTransform((hair > 0).astype(np.uint8), cv2.DIST_L2, 5)
    dist = cv2.GaussianBlur(dist, (0, 0), sig)
    dx, dy = cv2.Sobel(dist, cv2.CV_32F, 1, 0), cv2.Sobel(dist, cv2.CV_32F, 0, 1)
    phi = np.arctan2(dy, dx) + np.pi / 2
    w = np.clip((coh - 0.15) / 0.35, 0, 1)
    vx = w * np.cos(theta) + (1 - w) * np.cos(phi) * np.sign(np.cos(theta - phi) + 1e-6)
    vy = w * np.sin(theta) + (1 - w) * np.sin(phi) * np.sign(np.cos(theta - phi) + 1e-6)
    norm = np.hypot(vx, vy) + 1e-6
    vx, vy = vx / norm, vy / norm
    inside = cv2.erode(texture, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(fh * 0.03) | 1,) * 2)) > 0
    step, max_len = fh * 0.012, fh * 0.7
    gap = fh * 0.075
    ys, xs = np.mgrid[int(gap / 2):H:int(max(4, gap * 0.8)), int(gap / 2):W:int(max(4, gap * 0.8))]
    seeds = [(x, y) for x, y in zip(xs.ravel(), ys.ravel()) if inside[y, x]]
    # deepest seeds first: strands through the middle of the hair read best
    seeds.sort(key=lambda q: -dist[q[1], q[0]])
    lines, taken = [], np.zeros((H, W), np.uint8)

    def trace(x, y, sgn):
        pts, px, py = [], None, None
        for _ in range(int(max_len / step / 2)):
            xi, yi = int(x), int(y)
            if not (0 <= xi < W and 0 <= yi < H) or not inside[yi, xi] or taken[yi, xi]:
                break
            ux, uy = vx[yi, xi] * sgn, vy[yi, xi] * sgn
            if px is not None and ux * px + uy * py < 0:      # keep heading the same way
                ux, uy = -ux, -uy
            pts.append((x, y)); px, py = ux, uy
            x, y = x + ux * step, y + uy * step
        return pts

    for x, y in seeds:
        if taken[y, x]:
            continue
        a = trace(float(x), float(y), 1)
        b = trace(float(x), float(y), -1)
        pts = np.array(b[::-1] + a[1:]) if len(a) + len(b) > 2 else None
        if pts is None or len(pts) * step < 0.16 * fh:
            continue
        lines.append(pts[::2])
        cv2.polylines(taken, [pts.astype(np.int32)], False, 255, int(max(2, fh * 0.03)))
        if len(lines) >= n:
            break
    # a drawn strand tapers off before its ends
    return [ln[max(1, len(ln) // 10): len(ln) - max(1, len(ln) // 10)] for ln in lines if len(ln) > 6]


# --------------------------------------------------------------------------- exaggerating
def strength(detail):
    return STRENGTH * float(np.clip(detail, 0.0, 1.0))


SMOOTH_PASSES = 3


def _neighbours(xy, k=8):
    d2 = ((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1)
    return np.argsort(d2, axis=1)[:, 1:k + 1]


class Warp:
    """Moves any point in the photo the way the face moves when exaggerated: exactly with
    the mesh on the mesh, by inverse-distance blending of the nearest mesh points off it."""

    def __init__(self, m, k):
        self.src = m.P[:, :2]
        self.fh = m.face_h
        # The difference from the average is smoothed over each point's neighbours first:
        # the mesh's point-to-point jitter is noise, and multiplied it made every outline
        # wavy. What survives is feature-sized -- a nose, a jaw -- which is the caricature.
        diff = m.P - m.M
        nb = _neighbours(m.P[:, :2])
        for _ in range(SMOOTH_PASSES):
            diff = 0.5 * diff + 0.5 * diff[nb].mean(1)
        target = m.P + k * diff
        self.dst = target[:, :2]
        self.d = self.dst - self.src

    def __call__(self, pts):
        pts = np.asarray(pts, float).reshape(-1, 2)
        if len(pts) == 0:
            return pts
        d2 = ((pts[:, None, :] - self.src[None, :, :]) ** 2).sum(-1)
        idx = np.argsort(d2, axis=1)[:, :24]
        dd = np.take_along_axis(d2, idx, 1)
        w = 1.0 / (dd + (0.04 * self.fh) ** 2)
        w /= w.sum(1, keepdims=True)
        return pts + (w[..., None] * self.d[idx]).sum(1)


# --------------------------------------------------------------------------- drawing
@dataclass
class Drawing:
    """The caricature as lines, in the output picture's pixels."""
    shape: tuple
    found: bool
    lines: dict = field(default_factory=dict)       # part -> list of polylines
    irises: list = field(default_factory=list)      # (x, y, r)
    hatch: list = field(default_factory=list)
    hair_hatch: list = field(default_factory=list)
    construct: dict = field(default_factory=dict)
    th: int = 2
    light: int = 1
    folds: tuple = (0.0, 0.0, 0.0, 0.0)


_last = {}      # source image key -> the last Drawing made from it, for the guides


def drawing(img, detail):
    m = measure(img)
    H, W = img.shape[:2]
    if not m.found:
        return Drawing((H, W), False)
    k = strength(detail)
    warp = Warp(m, k)
    xy = warp.dst
    L = {}
    idx = lambda seq: xy[list(seq)]
    vis = m.jaw_visible
    outline, run = [], []
    for i, v in zip(list(FACE_OUTLINE) + [FACE_OUTLINE[0]], list(vis) + [vis[0]]):
        if v:
            run.append(xy[i])
        elif len(run) > 1:
            outline.append(np.array(run)); run = []
        else:
            run = []
    if len(run) > 1:
        outline.append(np.array(run))
    L["face"] = outline
    L["eyes_upper"] = [idx(u) for u, _ in EYES]
    L["eyes_lower"] = [idx(lo) for _, lo in EYES]
    L["brows"] = [(idx(u), idx(lo)) for u, lo in BROWS]
    L["nose"] = _cartoon_nose(xy)
    # the side of the nose away from the light, as one line down the bridge into the wing,
    # and a short curve under the tip -- the lines the icon's nose is made of
    across = xy[294] - xy[64]
    half = np.linalg.norm(across) / 2
    across = across / max(2 * half, 1e-6)
    sgn = -1.0 if m.light > 0 else 1.0          # lit from the image's left: shadow on the right
    sgn = -sgn
    ridge = [197, 195, 5]
    side = [xy[i] + across * sgn * half * f for i, f in zip(ridge, (0.22, 0.32, 0.42))]
    wing = xy[327 if sgn > 0 else 98]
    side.append(0.55 * side[-1] + 0.45 * wing)
    L["nose_side"] = [np.array(side)]
    L["nose_tip"] = []
    L["lips"] = [idx(LIP_TOP), idx(LIP_LINE), idx(LIP_OUTER_LOWER)]
    L["lip_detail"], L["chin"] = _mouth_and_chin(xy)
    L["folds"] = [line for line, _ in _fold_paths(xy)]
    L["hair"] = [warp(p) for p in m.hair]
    L["strands"] = [warp(p) for p in m.strands]
    irises = []
    for (x, y, r), (upper, lower) in zip(m.irises, EYES):
        # the iris moves and scales with its eye
        a0, b0 = m.P[upper[0], :2], m.P[upper[-1], :2]
        a1, b1 = xy[upper[0]], xy[upper[-1]]
        s = np.linalg.norm(b1 - a1) / max(np.linalg.norm(b0 - a0), 1e-6)
        c = warp([(x, y)])[0]
        irises.append((c[0], c[1], r * s))
    hatch = _hatch_lines(m.shadows, m.face_h / 34, 45 if m.light > 0 else 135, warp)
    hair_hatch = _hatch_lines(m.hair_dark, m.face_h / 22, 120 if m.light > 0 else 60, warp) \
        if m.hair_dark is not None else []

    # fit everything into the picture, centred, with a margin
    flat = [q for key, part in L.items() for p in part for q in (p if key == "brows" else (p,))]
    allp = np.vstack(flat + [np.array([[x - r, y - r], [x + r, y + r]]) for x, y, r in irises])
    lo, hi = allp.min(0), allp.max(0)
    margin = 0.06
    s = min(W * (1 - 2 * margin) / max(hi[0] - lo[0], 1), H * (1 - 2 * margin) / max(hi[1] - lo[1], 1))
    off = np.array([W, H]) / 2 - (lo + hi) / 2 * s
    F = lambda p: np.asarray(p) * s + off
    for key, part in L.items():
        L[key] = [(F(a), F(b)) for a, b in part] if key == "brows" else [F(p) for p in part]
    irises = [(*F((x, y)), r * s) for x, y, r in irises]
    # where the hair's outline runs right along the face's (under the jaw, beside the neck)
    # the face's line is the one kept: two parallel lines there read as a double chin
    if L["face"] and L["hair"]:
        face_pts = np.vstack(L["face"])
        L["hair"] = _drop_near(L["hair"], face_pts, 0.03 * m.face_h * s)
    # hatching only inside the drawing's own outline: strokes hanging past the last line
    # beside the jaw (where the hair's outline stops at the cut) read as smudges
    outline = [p for key in ("face", "hair", "strands") for p in L[key] if len(p) > 1]
    inside = np.zeros((H, W), np.uint8)
    if outline:
        cv2.fillPoly(inside, [cv2.convexHull(np.vstack(outline).astype(np.float32)).astype(np.int32)], 255)
    hatch = _clip(([F(p) for p in hatch]), inside)
    hair_hatch = _clip([F(p) for p in hair_hatch], inside)
    D = Drawing((H, W), True, L, irises, hatch, hair_hatch, th=max(1, int(round(max(H, W) / 380))), light=m.light,
                folds=m.folds)
    D.construct = _construction(F(xy), irises, L)
    _last[_key(img)] = D
    return D


def _bezier(a, c, b, t0=0.0, t1=1.0, n=16):
    t = np.linspace(t0, t1, n)[:, None]
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t ** 2 * b


def _fold_paths(xy):
    """The laugh lines (nasolabial folds) and cheek lines, placed from the mesh, each with the
    offset to a point just beside it: [(polyline, offset)] -- left fold, right fold, left
    cheek, right cheek. A laugh line runs from just outside the nose's wing down and out
    to just outside the mouth's corner, bowing out over the cheek; it stops short of the
    mouth, as drawn ones do. A cheek line is a short curve under the outer corner of the
    eye, following the cheekbone down and in."""
    mL, mR = xy[61], xy[291]
    mw = float(np.linalg.norm(mR - mL))
    if mw < 4:
        return []
    ex = (mR - mL) / mw
    ey = np.array([-ex[1], ex[0]])
    if np.dot(ey, xy[CHIN] - xy[2]) < 0:
        ey = -ey
    out = []
    for wing, corner, sgn in ((xy[64], mL, -1.0), (xy[294], mR, 1.0)):
        a = wing + ex * sgn * 0.08 * mw - ey * 0.03 * mw
        b = corner + ex * sgn * 0.12 * mw + ey * 0.05 * mw
        c = (a + b) / 2 + ex * sgn * 0.14 * mw
        out.append((_bezier(a, c, b, 0.05, 0.85), ex * sgn * 0.06 * mw))
    for eye_out, edge, sgn in ((xy[33], xy[234], -1.0), (xy[263], xy[454], 1.0)):
        ew = float(np.linalg.norm(xy[133] - xy[33])) if sgn < 0 else float(np.linalg.norm(xy[362] - xy[263]))
        a = eye_out * 0.7 + edge * 0.3 + ey * 0.45 * ew
        b = a + ey * 0.55 * ew - ex * sgn * 0.15 * ew
        c = (a + b) / 2 + ex * sgn * 0.12 * ew
        out.append((_bezier(a, c, b), ex * sgn * 0.08 * ew))
    return out


def _mean_along(gray, line):
    H, W = gray.shape
    q = np.round(line).astype(int)
    ok = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
    return float(gray[q[ok, 1], q[ok, 0]].mean()) if ok.any() else 0.0


def _mouth_and_chin(xy):
    """The lines that give a cartoon mouth its shape, from the mesh: the two ridges from the
    nose down to the peaks of the upper lip, a tick at each corner of the mouth, a few short
    strokes across each lip for its fullness, the shadow under the lower lip, and the
    curve of the chin above its outline."""
    left, right = xy[61], xy[291]
    width = float(np.linalg.norm(right - left))
    if width < 4:
        return [], []
    ex = (right - left) / width
    ey = np.array([-ex[1], ex[0]])
    if np.dot(ey, xy[CHIN] - xy[2]) < 0:
        ey = -ey
    detail = []
    # the philtrum: from under the nose to each peak of the cupid's bow, the lower half only
    for peak, top in ((xy[37], xy[2] - ex * 0.1 * width), (xy[267], xy[2] + ex * 0.1 * width)):
        detail.append(np.array([top * 0.45 + peak * 0.55, peak - ey * 0.04 * width]))
    # a tick at each corner, turning up or down with the mouth's own curve
    line = xy[list(LIP_LINE)]
    for end, nxt, sgn in ((line[0], line[1], -1), (line[-1], line[-2], 1)):
        d = (end - nxt) / (np.linalg.norm(end - nxt) + 1e-6)
        detail.append(np.array([end, end + d * 0.06 * width + ey * 0.05 * width]))
    # fullness: a few short strokes across the lower lip, fanning with its curve
    low_o, low_i = xy[list(LIP_OUTER_LOWER)], xy[list((78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308))]
    for outer, inner, ts in ((low_o, low_i, (0.32, 0.5, 0.68)),):
        for t in ts:
            a, b = _along(inner, t), _along(outer, t)
            detail.append(np.array([a * 0.75 + b * 0.25, a * 0.3 + b * 0.7]))
    # the shadow under the lower lip, and the chin's curve above its outline
    lip_bottom, chin = xy[17], xy[CHIN]
    drop = float(np.linalg.norm(chin - lip_bottom))

    def arc(c, rx, ry, a0, a1, n=12):
        t = np.radians(np.linspace(a0, a1, n))
        return np.array([c + ex * rx * np.cos(a) + ey * ry * np.sin(a) for a in t])
    chin_lines = [arc(lip_bottom + ey * 0.32 * drop, 0.22 * width, 0.12 * drop, 200, 340),   # under the lip
                  arc(lip_bottom + ey * 0.55 * drop, 0.30 * width, 0.28 * drop, 25, 155)]    # the chin pad
    return detail, chin_lines


def _drop_near(polys, pts, dist):
    """The parts of each polyline farther than `dist` from every point in `pts`."""
    out = []
    for p in polys:
        d = np.min(np.hypot(p[:, None, 0] - pts[None, :, 0], p[:, None, 1] - pts[None, :, 1]), axis=1)
        run = []
        for q, far in zip(p, d > dist):
            if far:
                run.append(q)
            elif len(run) > 2:
                out.append(np.array(run)); run = []
            else:
                run = []
        if len(run) > 2:
            out.append(np.array(run))
    return out


def _clip(polys, mask):
    """The parts of each polyline that lie inside `mask`."""
    H, W = mask.shape
    out = []
    for p in polys:
        q = np.round(p).astype(int)
        ok = (q[:, 0] >= 0) & (q[:, 0] < W) & (q[:, 1] >= 0) & (q[:, 1] < H)
        ok[ok] = mask[q[ok, 1], q[ok, 0]] > 0
        run = []
        for pt, v in zip(p, ok):
            if v:
                run.append(pt)
            elif len(run) > 1:
                out.append(np.array(run)); run = []
            else:
                run = []
        if len(run) > 1:
            out.append(np.array(run))
    return out


def _cartoon_nose(xy):
    """The nose as a cartoonist draws it from the front: a curl round each wing, from above
    the wing, out and down into the nostril, and a soft curve under the tip. Seen face-on
    the mesh's own lower edge of the nose is nearly a straight line, which drew as two
    dashes; these curves are placed and sized from the mesh -- the wings, the tip and the
    base -- and turned with the head."""
    lw, rw = (xy[64] + xy[98]) / 2, (xy[294] + xy[327]) / 2
    width = float(np.linalg.norm(rw - lw))
    if width < 3:
        return []
    ex = (rw - lw) / width                      # across the face
    ey = np.array([-ex[1], ex[0]])              # down the face
    if np.dot(ey, xy[2] - xy[168]) < 0:
        ey = -ey
    tip, base = xy[4], xy[2]

    def arc(c, rx, ry, a0, a1, n=14):
        t = np.radians(np.linspace(a0, a1, n))
        return np.array([c + ex * rx * np.cos(a) + ey * ry * np.sin(a) for a in t])
    r = 0.13 * width
    left = arc(lw + ex * 0.4 * r - ey * 0.2 * r, r, 1.15 * r, 215, 75)       # up-left, round, into the nostril
    right = arc(rw - ex * 0.4 * r - ey * 0.2 * r, r, 1.15 * r, -35, 105)
    under = arc((tip + base) / 2 - ey * 0.25 * r, 0.9 * r, 0.55 * r, 35, 145)  # the curve under the tip
    return [left, right, under]


def _hatch_lines(mask, spacing, angle, warp):
    """Parallel strokes over a mask, as polylines in the photo's pixels, then warped."""
    if mask is None or not mask.any():
        return []
    H, W = mask.shape
    t = np.radians(angle)
    d, n = np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])
    ys, xs = np.nonzero(mask)
    pts = np.c_[xs, ys].astype(float)
    proj_n, proj_d = pts @ n, pts @ d
    lines = []
    step = max(1.0, spacing / 6)
    for c in np.arange(proj_n.min() + spacing / 2, proj_n.max(), spacing):
        a = np.arange(proj_d.min(), proj_d.max(), step)
        q = c * n[None] + a[:, None] * d[None]
        qi = q.astype(int)
        ok = (qi[:, 0] >= 0) & (qi[:, 0] < W) & (qi[:, 1] >= 0) & (qi[:, 1] < H)
        inside = np.zeros(len(q), bool)
        inside[ok] = mask[qi[ok, 1], qi[ok, 0]] > 0
        run = []
        for p, v in zip(q, inside):
            if v:
                run.append(p)
            else:
                if len(run) >= 3:
                    lines.append(np.array(run))
                run = []
        if len(run) >= 3:
            lines.append(np.array(run))
    # shorten each stroke a little at both ends: hatching that stops short of an edge
    # reads as shading; hatching that touches it reads as a pattern
    out = []
    for ln in lines:
        k = max(1, len(ln) // 8)
        if len(ln) > 2 * k + 1:
            out.append(warp(ln[k:-k]))
    return out


def _construction(xy, irises, L):
    """The simple shapes the steps start from: head, centre line, feature lines and shapes."""
    face = xy[list(FACE_OUTLINE)].astype(np.float32)
    head = cv2.fitEllipse(face)
    eye_c = [np.array(i[:2]) for i in irises]
    root, chin, base = xy[NOSE_ROOT], xy[CHIN], xy[2]
    mouth = (xy[61] + xy[291]) / 2
    shapes = {
        "eyes": [cv2.fitEllipse(np.vstack([u, lo]).astype(np.float32)) for u, lo in zip(L["eyes_upper"], L["eyes_lower"])],
        "nose": np.array([root, xy[64], xy[2], xy[294]]),
        "mouth": cv2.fitEllipse(xy[list(LIP_OUTER_LOWER)].astype(np.float32)),
    }
    hair = [p for p in L["hair"] if len(p) > 2]
    hull = cv2.convexHull(np.vstack(hair).astype(np.float32)).reshape(-1, 2) if hair else None
    return dict(head=head, hair_mass=hull, centre=(root, chin), eye_line=tuple(eye_c),
                nose=base, mouth=mouth, chin=chin, shapes=shapes,
                mouth_corners=(xy[61], xy[291]))


# --------------------------------------------------------------------------- rendering
def _chaikin(p, n=2, closed=False):
    """Corner-cutting: turns the mesh's few points per feature into a smooth curve."""
    p = np.asarray(p, float)
    for _ in range(n):
        if len(p) < 3:
            break
        q = p if not closed else np.vstack([p, p[:1]])
        a, b = q[:-1], q[1:]
        mid = np.empty((2 * len(a), 2))
        mid[0::2], mid[1::2] = 0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b
        p = mid if closed else np.vstack([q[:1], mid, q[-1:]])
    return p


def _poly(out, p, colour, th, closed=False, smooth=True):
    if p is None or len(p) < 2:
        return
    if smooth and len(p) <= 60:
        p = _chaikin(p, 2, closed)
    cv2.polylines(out, [np.round(np.asarray(p) * 4).astype(np.int32)], closed, colour, th, cv2.LINE_AA, shift=2)


def _brow(out, upper, lower, th):
    """A brow drawn the way the icon draws it: a soft tapered shape, full at the inner
    end and thinning to a point at the outer, filled with short hair strokes that lean
    from the inner end outwards, and its top edge lightly inked."""
    n = 16
    top = np.array([_along(upper, t) for t in np.linspace(0, 1, n)])
    bot = np.array([_along(lower, t) for t in np.linspace(0, 1, n)])
    tt = np.linspace(0, 1, n)
    taper = np.interp(tt, (0, 0.75, 1.0), (0.3, 1.25, 0.85))[:, None]   # thin out, full, rounded in
    mid = (top + bot) / 2
    top, bot = mid + (top - mid) * taper, mid + (bot - mid) * taper
    shape = np.vstack([top, bot[::-1]])
    cv2.fillPoly(out, [np.round(shape * 4).astype(np.int32)], (150, 150, 150), cv2.LINE_AA, shift=2)
    m = 30
    for i, t in enumerate(np.linspace(0.03, 0.99, m)):
        lo = 0.05 + 0.3 * ((i * 7) % 5) / 4                  # stagger where each hair starts
        a = _along(bot, t) + (_along(top, t) - _along(bot, t)) * lo
        t2 = max(0.0, t - 0.16)
        b = _along(top, t2) * 0.9 + _along(bot, t2) * 0.1
        _poly(out, np.array([a, (a + b) / 2 + (_along(top, t) - _along(bot, t)) * 0.12, b]), (30, 30, 30),
              max(1, th))
    _poly(out, top, (60, 60, 60), max(1, th - 1))


def _normal(p, i, centre):
    """Unit normal to a polyline at point i, pointing away from `centre`."""
    a, b = p[max(0, i - 1)], p[min(len(p) - 1, i + 1)]
    t = (b - a) / (np.linalg.norm(b - a) + 1e-6)
    nrm = np.array([-t[1], t[0]])
    return nrm if np.dot(p[i] - centre, nrm) > 0 else -nrm


def _eye_details(out, upper, lower, th):
    """What the icon's eyes have that makes them look alive: a heavier upper lid, a crease
    above it, lashes that sweep out from the outer half, a little lower lash at the outer
    corner, and the tear duct. Index 0 of each lid is the outer corner."""
    up = _chaikin(upper, 2)
    lo = _chaikin(lower, 2)
    centre = (up.mean(0) + lo.mean(0)) / 2
    height = float(np.linalg.norm(_along(up, 0.5) - _along(lo, 0.5)))
    width = float(np.linalg.norm(up[0] - up[-1]))
    if width < 4:
        return
    opening = max(height, 0.18 * width)
    # the crease: the upper lid lifted, over its middle, thin and soft
    crease = []
    for t in np.linspace(0.12, 0.88, 14):
        q = _along(up, t)
        i = int(np.argmin(np.hypot(*(up - q).T)))
        crease.append(q + _normal(up, i, centre) * opening * (0.55 + 0.25 * np.sin(np.pi * t)))
    _poly(out, np.array(crease), (95, 95, 95), max(1, th - 1))
    # lashes: from the outer corner to past the middle, longest at the corner, curling out
    outer_dir = (up[0] - up[-1]) / (width + 1e-6)
    for t in np.linspace(0.02, 0.5, 6):
        q = _along(up, t)
        i = int(np.argmin(np.hypot(*(up - q).T)))
        n = _normal(up, i, centre)
        d = n * 0.7 + outer_dir * (0.3 + 0.6 * (1 - t / 0.5))
        d /= np.linalg.norm(d) + 1e-6
        length = opening * (0.22 + 0.33 * (1 - t / 0.5))
        tip = q + d * length
        mid = q + d * length * 0.5 + n * length * 0.12
        _poly(out, np.array([q, mid, tip]), INK, max(1, th - 1))
    # a few short lower lashes at the outer corner
    for t in (0.12, 0.22, 0.32):
        q = _along(lo, t)
        i = int(np.argmin(np.hypot(*(lo - q).T)))
        n = _normal(lo, i, centre)
        _poly(out, np.array([q, q + (n * 0.8 + outer_dir * 0.4) * opening * 0.18]), (90, 90, 90), 1, smooth=False)
    # the heavy upper lid, thickest over the middle-to-outer part, and the tear duct
    _poly(out, up, INK, th + 1, smooth=False)
    _poly(out, up[: int(len(up) * 0.7)], INK, th + 2, smooth=False)
    duct = [up[-1] + (up[-1] - centre) * 0.02, lo[-1] + (lo[-1] - up[-1]) * 0.6 + (centre - up[-1]) * 0.08]
    _poly(out, np.array(duct), INK, max(1, th - 1), smooth=False)


def _along(p, t):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    x = t * d[-1]
    return np.array([np.interp(x, d, p[:, 0]), np.interp(x, d, p[:, 1])])


def paint(D, parts=None, hatch=True, base=None, faded=None):
    """Rasterise a Drawing. `parts` limits which parts are drawn (for the steps)."""
    H, W = D.shape
    out = np.full((H, W, 3), 255, np.uint8) if base is None else base.copy()
    if not D.found:
        return out
    th = D.th
    want = (lambda k: True) if parts is None else (lambda k: k in parts)
    if want("face"):
        for p in D.lines["face"]:
            _poly(out, p, INK, th)
    if want("hair"):
        # the hair's outline is what says "hair" from across the room: drawn as heavy as the
        # upper lids, the heaviest line on the page, so the shape of the hair reads first
        for p in D.lines["hair"]:
            _poly(out, p, INK, th + 1)
    if want("strands"):
        for p in D.lines["strands"]:
            _poly(out, p, INK, max(1, th - 1))
    if want("brows"):
        for u, lo in D.lines["brows"]:
            _brow(out, u, lo, max(1, th - 1))
    if want("eyes"):
        for x, y, r in D.irises:
            _iris(out, x, y, r, th)
        # the lids cover the top and bottom of the iris: paint the eye's outside back white
        for u, lo, iris in zip(D.lines["eyes_upper"], D.lines["eyes_lower"], D.irises):
            _mask_outside_eye(out, u, lo, [iris], th)
        for lo in D.lines["eyes_lower"]:
            _poly(out, lo[1:-1], (80, 80, 80), max(1, th - 1))
        for u, lo in zip(D.lines["eyes_upper"], D.lines["eyes_lower"]):
            _eye_details(out, u, lo, th)
    if want("nose"):
        for p in D.lines["nose"]:
            _poly(out, p, INK, th)
        for p in D.lines.get("nose_side", []):
            _poly(out, p, INK, max(1, th - 1))
        for p in D.lines.get("nose_tip", []):
            _poly(out, p, (70, 70, 70), max(1, th - 1))
    if want("lips"):
        top, line, lower = D.lines["lips"]
        _poly(out, top, INK, th)
        _poly(out, line, INK, th + 1)
        _poly(out, lower[2:-2], INK, th)                     # the lower lip, short of the corners
        for p in D.lines.get("lip_detail", []):
            _poly(out, p, (90, 90, 90), max(1, th - 1), smooth=False)
    if want("folds"):
        # laugh lines and cheek lines: always there, as in the icon, but faint where the
        # photo shows none and darker as the photo's own fold deepens
        for p, depth in zip(D.lines.get("folds", []), D.folds):
            g = int(140 - 80 * depth)
            _poly(out, p, (g, g, g), max(1, th - 1))
    if want("chin"):
        for p in D.lines.get("chin", []):
            _poly(out, p, (70, 70, 70), max(1, th - 1))
    if hatch and want("hatch"):
        for p in D.hatch:
            _poly(out, p, HATCH, max(1, th - 1))
        for p in D.hair_hatch:
            _poly(out, p, HATCH, max(1, th - 1))
    return out


def _iris(out, x, y, r, th):
    """An iris with some life in it: a dark rim, a few fibres from the pupil, a shadow
    from the upper lid across its top, a large pupil and a bright catchlight."""
    c = (int(round(x)), int(round(y)))
    R = max(2, int(round(r)))
    cv2.circle(out, c, R, (150, 150, 150), -1, cv2.LINE_AA)               # the iris's tone
    cv2.circle(out, c, R, INK, th + 1, cv2.LINE_AA)                       # its dark rim
    for a in np.linspace(0, 2 * np.pi, 14, endpoint=False):               # fibres
        p0 = (x + np.cos(a) * r * 0.5, y + np.sin(a) * r * 0.5)
        p1 = (x + np.cos(a) * r * 0.85, y + np.sin(a) * r * 0.85)
        cv2.line(out, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), (100, 100, 100), 1, cv2.LINE_AA)
    cv2.ellipse(out, c, (R, R), 0, 200, 340, (70, 70, 70), max(1, int(r * 0.35)), cv2.LINE_AA)   # lid shadow
    cv2.circle(out, c, max(1, int(round(r * 0.48))), (25, 25, 25), -1, cv2.LINE_AA)               # pupil
    cv2.circle(out, (int(round(x + r * 0.3)), int(round(y - r * 0.32))), max(1, int(round(r * 0.22))),
               (255, 255, 255), -1, cv2.LINE_AA)                                                  # catchlight
    cv2.circle(out, (int(round(x - r * 0.28)), int(round(y + r * 0.3))), max(1, int(round(r * 0.09))),
               (235, 235, 235), -1, cv2.LINE_AA)


def _mask_outside_eye(out, upper, lower, irises, th):
    """Redraw the iris clipped to the opening between the lids."""
    H, W = out.shape[:2]
    eye = np.zeros((H, W), np.uint8)
    cv2.fillPoly(eye, [np.round(np.vstack([upper, lower[::-1]])).astype(np.int32)], 255)
    ring = np.zeros((H, W), np.uint8)
    for x, y, r in irises:
        cv2.circle(ring, (int(round(x)), int(round(y))), int(round(r)) + th + 1, 255, -1)
    spill = (ring > 0) & (eye == 0)
    # keep the lid lines themselves
    lids = np.zeros((H, W), np.uint8)
    _poly(lids, upper, 255, th + 2)
    _poly(lids, lower, 255, th + 1)
    out[spill & (lids == 0)] = 255
    _poly(out, upper, INK, th + 1)


def paint_construction(D, level=2, base=None):
    """The construction, in the soft line, for the Shapes style and the first steps."""
    H, W = D.shape
    out = np.full((H, W, 3), 255, np.uint8) if base is None else base.copy()
    if not D.found:
        return out
    c, th = D.construct, D.th
    (cx, cy), (a, b), ang = c["head"]
    cv2.ellipse(out, (int(cx), int(cy)), (int(a / 2), int(b / 2)), ang, 0, 360, SOFT, th, cv2.LINE_AA)
    if c["hair_mass"] is not None:
        _poly(out, c["hair_mass"], SOFT, max(1, th - 1), closed=True)
    root, chin = c["centre"]
    d = (chin - root) / (np.linalg.norm(chin - root) + 1e-6)
    _poly(out, np.array([root - d * b * 0.25, chin + d * b * 0.05]), SOFT, max(1, th - 1))
    if len(c["eye_line"]) == 2:
        e0, e1 = c["eye_line"]
        v = (e1 - e0) / (np.linalg.norm(e1 - e0) + 1e-6)
        _poly(out, np.array([e0 - v * a * 0.35, e1 + v * a * 0.35]), SOFT, max(1, th - 1))
        for y_at in (c["nose"], c["mouth"]):
            _poly(out, np.array([y_at - v * a * 0.25, y_at + v * a * 0.25]), SOFT, max(1, th - 1))
    if level >= 2:
        for (ex, ey), (ea, eb), eang in c["shapes"]["eyes"]:
            cv2.ellipse(out, (int(ex), int(ey)), (int(ea / 2), int(eb / 2)), eang, 0, 360, SOFT, th, cv2.LINE_AA)
        _poly(out, c["shapes"]["nose"], SOFT, th, closed=True)
        (mx, my), (ma, mb), mang = c["shapes"]["mouth"]
        cv2.ellipse(out, (int(mx), int(my)), (int(ma / 2), int(mb / 2)), mang, 0, 360, SOFT, th, cv2.LINE_AA)
    return out


def why_not(img):
    """Why no caricature was drawn: the models, or no face. In words a person can act on."""
    from . import landmarks
    reason = landmarks.unavailable_reason()
    if reason:
        return "Can't draw the cartoon: " + reason
    return "No face found in this crop - tap a face in a portrait"


def _fallback(img):
    """No caricature: say why in the picture, large enough to read."""
    H, W = img.shape[:2]
    out = np.full((H, W, 3), 255, np.uint8)
    words, lines, cur = why_not(img).split(), [], ""
    fs = max(0.5, W / 520)
    for w in words:                                  # wrap to the picture's width
        t = (cur + " " + w).strip()
        if cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)[0][0] > W * 0.9 and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    lines.append(cur)
    lh = int(cv2.getTextSize("Ag", cv2.FONT_HERSHEY_SIMPLEX, fs, 1)[0][1] * 1.8)
    y = H // 2 - lh * (len(lines) - 1) // 2
    for ln in lines:
        tw = cv2.getTextSize(ln, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)[0][0]
        cv2.putText(out, ln, (max(4, (W - tw) // 2), y), cv2.FONT_HERSHEY_SIMPLEX, fs, (70, 70, 70),
                    max(1, int(fs * 1.5)), cv2.LINE_AA)
        y += lh
    return out


def caricature_lines(img, d=0.5):
    D = drawing(img, d)
    return paint(D, hatch=False) if D.found else _fallback(img)


def caricature_hatched(img, d=0.5):
    D = drawing(img, d)
    return paint(D, hatch=True) if D.found else _fallback(img)

