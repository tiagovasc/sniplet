"""Conservative, sampled visual checks. Pixel limits use a reference width of 854."""
import cv2
import numpy as np

LIPS = [61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91]


def compare(a, b, scale=1):
    metrics = {}
    for name, ids, limit in [('face', [0, 2, 5], 10), ('shoulders', [11, 12], 14), ('wrists', [15, 16], 20)]:
        good = [i for i in ids if a['pose'][i, 2] >= .65 and b['pose'][i, 2] >= .65]
        if name != 'wrists' and len(good) != len(ids):
            return dict(accepted=False, reason='required body landmarks missing', metrics=metrics)
        value = float(np.max(np.linalg.norm(a['pose'][good, :2] - b['pose'][good, :2], axis=1))) if good else None
        metrics[name] = value
        if value is not None and value > limit * scale:
            return dict(accepted=False, reason=f'{name} movement', metrics=metrics)
    la, lb = a['face'], b['face']
    metrics['lips'] = float(np.max(np.linalg.norm(la[LIPS]-lb[LIPS], axis=1)))
    metrics['mouth_opening'] = float(abs(np.linalg.norm(la[13]-la[14]) - np.linalg.norm(lb[13]-lb[14])))
    metrics['mouth_width'] = float(abs(np.linalg.norm(la[61]-la[291]) - np.linalg.norm(lb[61]-lb[291])))
    okay = all(metrics[k] <= v * scale for k,v in [('lips',8), ('mouth_opening',3), ('mouth_width',4)])
    return dict(accepted=okay, reason='landmarks match' if okay else 'mouth movement', metrics=metrics)


class Judge:
    def __init__(self, path, scale=1):
        import mediapipe as mp
        self.cap = cv2.VideoCapture(str(path))
        self.scale = scale
        self.pose = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=1, min_detection_confidence=.6)
        self.face = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=2, refine_landmarks=True, min_detection_confidence=.6)

    def close(self):
        self.cap.release()
        self.pose.close()
        self.face.close()

    def sample(self, time):
        self.cap.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
        ok, image = self.cap.read()
        if not ok:
            return None
        h, w = image.shape[:2]
        image = cv2.resize(image, (854, round(h * 854 / w)))
        h, w = image.shape[:2]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        faces = self.face.process(rgb).multi_face_landmarks
        pose = self.pose.process(rgb).pose_landmarks
        if not faces or len(faces) != 1 or not pose:
            return None
        p = np.array([[v.x*w, v.y*h, v.visibility] for v in pose.landmark])
        p[(p[:,0] < 0) | (p[:,0] >= w) | (p[:,1] < 0) | (p[:,1] >= h), 2] = 0
        f = np.array([[v.x*w, v.y*h] for v in faces[0].landmark])
        if np.linalg.norm(p[0,:2] - f[1]) > 60:
            return None
        # Exclude the speaker and a margin from background motion estimation.
        visible = p[p[:,2] >= .5, :2]
        points = np.concatenate([visible, f])
        x0, y0 = np.maximum(points.min(axis=0) - [60,40], 0).astype(int)
        x1, y1 = np.minimum(points.max(axis=0) + [60,60], [w,h]).astype(int)
        mask = np.full((h,w),255,np.uint8)
        mask[y0:y1,x0:x1] = 0
        return dict(pose=p, face=f, gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY), mask=mask)

    def background(self, a, b):
        mask = cv2.bitwise_and(a['mask'], b['mask'])
        points = cv2.goodFeaturesToTrack(a['gray'], maxCorners=150, qualityLevel=.015, minDistance=8, mask=mask)
        if points is None or len(points) < 12:
            return None
        moved, status, error = cv2.calcOpticalFlowPyrLK(a['gray'], b['gray'], points, None)
        if moved is None:
            return None
        back, reverse_status, _ = cv2.calcOpticalFlowPyrLK(b['gray'], a['gray'], moved, None)
        if back is None:
            return None
        good = (status.ravel()==1) & (reverse_status.ravel()==1) & (error.ravel()<20) & (np.linalg.norm(back-points,axis=2).ravel()<1)
        if good.sum() < max(12, len(points)*.5):
            return None
        return float(np.percentile(np.linalg.norm(moved[good]-points[good], axis=2), 75))

    def __call__(self, before, after):
        # Sample endpoints and intervening frames; missing/multiple faces veto.
        samples = [self.sample(t) for t in np.linspace(before, after, max(3, int((after-before)*4)+1))]
        if any(s is None for s in samples):
            return dict(accepted=False, reason='single face/body tracking unavailable')
        check = compare(samples[0], samples[-1], self.scale)
        if not check['accepted']:
            return check
        motion = [self.background(samples[0], s) for s in samples[1:]]
        if any(v is None for v in motion):
            return dict(**{**check, 'accepted':False, 'reason':'insufficient reliable background tracking'})
        check['metrics']['background'] = max(motion)
        if max(motion) > 1.5 * self.scale:
            check.update(accepted=False, reason='camera/background movement')
        return check
