"""Vendored from OpenCV Zoo (https://github.com/opencv/opencv_zoo), Apache License 2.0.

MediaPipe person detection. Kept close to upstream so it can be re-synced; the one change
is that the anchor grid is generated instead of being listed as ~2250 lines of constants
(see `_load_anchors`). See vendor/LICENSE for the licence and attribution.
"""
import numpy as np
import cv2 as cv

class MPPersonDet:
    def __init__(self, modelPath, nmsThreshold=0.3, scoreThreshold=0.5, topK=5000, backendId=0, targetId=0):
        self.model_path = modelPath
        self.nms_threshold = nmsThreshold
        self.score_threshold = scoreThreshold
        self.topK = topK
        self.backend_id = backendId
        self.target_id = targetId

        self.input_size = np.array([224, 224]) # wh

        self.model = cv.dnn.readNet(self.model_path)
        self.model.setPreferableBackend(self.backend_id)
        self.model.setPreferableTarget(self.target_id)

        self.anchors = self._load_anchors()

    @property
    def name(self):
        return self.__class__.__name__

    def setBackendAndTarget(self, backendId, targetId):
        self.backend_id = backendId
        self.target_id = targetId
        self.model.setPreferableBackend(self.backend_id)
        self.model.setPreferableTarget(self.target_id)

    def _preprocess(self, image):
        pad_bias = np.array([0., 0.]) # left, top
        image = cv.cvtColor(image, cv.COLOR_BGR2RGB)
        image = image.astype(np.float32) / 255.0 # norm
        image = (image - 0.5) * 2 # [0, 1] -> [-1, 1]
        ratio = min(self.input_size / image.shape[:2])
        if image.shape[0] != self.input_size[0] or image.shape[1] != self.input_size[1]:
            # keep aspect ratio when resize
            ratio_size = (np.array(image.shape[:2]) * ratio).astype(np.int32)
            image = cv.resize(image, (ratio_size[1], ratio_size[0]))
            pad_h = self.input_size[0] - ratio_size[0]
            pad_w = self.input_size[1] - ratio_size[1]
            pad_bias[0] = left = pad_w // 2
            pad_bias[1] = top = pad_h // 2
            right = pad_w - left
            bottom = pad_h - top
            image = cv.copyMakeBorder(image, top, bottom, left, right, cv.BORDER_CONSTANT, None, (0, 0, 0))

        blob = np.transpose(image, [2, 0, 1])
        pad_bias = (pad_bias / ratio).astype(np.int32)
        return blob[np.newaxis, :, :, :], pad_bias # chw -> nchw

    def infer(self, image):
        h, w, _ = image.shape

        # Preprocess
        input_blob, pad_bias = self._preprocess(image)

        # Forward
        self.model.setInput(input_blob)
        output_blob = self.model.forward(self.model.getUnconnectedOutLayersNames())

        # Postprocess
        results = self._postprocess(output_blob, np.array([w, h]), pad_bias)

        return results

    def _postprocess(self, output_blob, original_shape, pad_bias):
        score = output_blob[1][0, :, 0]
        box_delta = output_blob[0][0, :, 0:4]
        landmark_delta = output_blob[0][0, :, 4:]
        scale = max(original_shape)

        # get scores
        score = score.astype(np.float64)
        score = np.clip(score, -100, 100)
        score = 1 / (1 + np.exp(-score))

        # get boxes
        cxy_delta = box_delta[:, :2] / self.input_size
        wh_delta = box_delta[:, 2:] / self.input_size
        xy1 = (cxy_delta - wh_delta / 2 + self.anchors) * scale
        xy2 = (cxy_delta + wh_delta / 2 + self.anchors) * scale
        boxes = np.concatenate([xy1, xy2], axis=1)
        boxes -= [pad_bias[0], pad_bias[1], pad_bias[0], pad_bias[1]]
        # NMS
        keep_idx = cv.dnn.NMSBoxes(boxes, score, self.score_threshold, self.nms_threshold, top_k=self.topK)
        if len(keep_idx) == 0:
            return np.empty(shape=(0, 13))
        selected_score = score[keep_idx]
        selected_box = boxes[keep_idx]

        # get landmarks
        selected_landmarks = landmark_delta[keep_idx].reshape(-1, 4, 2)
        selected_landmarks = selected_landmarks / self.input_size
        selected_anchors = self.anchors[keep_idx]
        for idx, landmark in enumerate(selected_landmarks):
            landmark += selected_anchors[idx]
        selected_landmarks *= scale
        selected_landmarks -= pad_bias

        # TODO: still don't know the meaning of face bbox
        # each landmark: hip center point; full body point; shoulder center point; upper body point;
        #
        # [
        #   [face_bbox, landmarks, score]
        #   ...
        #   [face_bbox, landmarks, score]
        # ]
        return np.c_[selected_box.reshape(-1, 4), selected_landmarks.reshape(-1, 8), selected_score.reshape(-1, 1)]

    def _load_anchors(self):
        """The SSD anchor grid, generated rather than tabulated.

        Upstream ships 2254 anchor pairs as a literal array, about 2250 lines. They are
        three feature maps over a 224px input: 28x28 at stride 8 with two anchors per
        cell, 14x14 at stride 16 with two, and 7x7 at stride 32 with six. Generating them
        reproduces the published table exactly (checked in tests/test_body.py).
        """
        size = self.input_size[0]
        out = []
        for stride, per_cell in ((8, 2), (16, 2), (32, 6)):
            g = size // stride
            cy, cx = np.mgrid[0:g, 0:g]
            centres = np.stack([(cx + 0.5) * stride / size,
                                (cy + 0.5) * stride / size], axis=-1).reshape(-1, 2)
            out.append(np.repeat(centres, per_cell, axis=0))
        return np.concatenate(out).astype(np.float32)

