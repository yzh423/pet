# coding: utf-8
"""
PySOT single-object tracking + serial commands to Arduino Mega 2560 (comm.py).

Video source: USB webcam (OpenCV), default 1920×1080 request via --cap-width / --cap-height.

Follow logic: target centroid vs image center -> turn toward target; centered -> forward.
"""
import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
import torch

_ROOT = Path(__file__).resolve().parent


def _is_pysot_repo(path: Path) -> bool:
    return path.is_dir() and (path / "pysot").is_dir() and (path / "setup.py").is_file()


def _find_pysot_root() -> Path:
    """Prefer bundled ``pysot-master/`` (STVIR PySOT tree), then sibling ``pysot/`` if present."""
    env = (os.environ.get("PYSOT_HOME") or "").strip()
    if env:
        p = Path(env).expanduser()
        if _is_pysot_repo(p):
            return p
        raise RuntimeError("PYSOT_HOME is not a PySOT repo root (need setup.py + pysot/): %s" % (p,))
    for name in ("pysot-master", "pysot"):
        p = _ROOT / name
        if _is_pysot_repo(p):
            return p
    raise RuntimeError(
        "PySOT not found. This repo expects ``pysot-master/`` next to jetson_follow_track.py "
        "(upstream: https://github.com/STVIR/pysot). Build with:\n"
        "  cd pysot-master && python setup.py build_ext --inplace\n"
        "Or clone alongside: git clone https://github.com/STVIR/pysot.git pysot\n"
        "Or set PYSOT_HOME. See MODEL_ZOO.md for weights."
    )


_PYSOT = _find_pysot_root()
sys.path.insert(0, str(_PYSOT))

import comm  # noqa: E402

from pysot.core.config import cfg  # noqa: E402
from pysot.models.model_builder import ModelBuilder  # noqa: E402
from pysot.tracker.tracker_builder import build_tracker  # noqa: E402

torch.set_num_threads(1)


def _load_checkpoint_snapshot(path: str):
    """
    Load PySOT weights. Prefer weights_only=True (PyTorch 2+) to reduce pickle RCE risk
    from untrusted .pth files; fall back on older torch without that argument.
    Only load checkpoints from sources you trust.
    """
    kw: dict = {"map_location": lambda storage, loc: storage.cpu()}
    try:
        return torch.load(path, weights_only=True, **kw)
    except TypeError:
        return torch.load(path, **kw)


def resize_track(frame, max_w):
    # type: (np.ndarray, int) -> Tuple[np.ndarray, float]
    h, w = frame.shape[:2]
    if w <= max_w:
        return frame, 1.0
    scale = max_w / float(w)
    nw = max_w
    nh = int(round(h * scale))
    return cv2.resize(frame, (nw, nh)), scale


def parse_bbox(s):
    # type: (str) -> Tuple[int, int, int, int]
    parts = [int(x.strip()) for x in s.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise ValueError("init-bbox must be x,y,w,h")
    return parts[0], parts[1], parts[2], parts[3]


def open_webcam(device: int, cap_width: int, cap_height: int) -> cv2.VideoCapture:
    # Prefer V4L2 on Linux (Jetson / Ubuntu) for more stable USB cameras.
    if sys.platform.startswith("linux"):
        cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if not cap.isOpened():
            cap = cv2.VideoCapture(device)
    else:
        cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open webcam device index {device}")
    if cap_width > 0:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cap_width)
    if cap_height > 0:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cap_height)
    for _ in range(5):
        cap.read()
    return cap


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PySOT visual follow: USB 1080p webcam + Arduino serial"
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="Webcam index (default 0)",
    )
    parser.add_argument(
        "--cap-width",
        type=int,
        default=1920,
        help="Webcam capture width; 0 = do not set (driver default)",
    )
    parser.add_argument(
        "--cap-height",
        type=int,
        default=1080,
        help="Webcam capture height; 0 = do not set",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(
            _PYSOT
            / "experiments"
            / "siamrpn_mobilev2_l234_dwxcorr"
            / "config.yaml"
        ),
        help="PySOT config.yaml (MobileNetV2 is lighter on Nano)",
    )
    parser.add_argument(
        "--snapshot",
        type=str,
        required=True,
        help="PySOT model.pth (download from PySOT MODEL_ZOO.md)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=640,
        help="Resize width for tracking (speed on Nano / PC)",
    )
    parser.add_argument(
        "--deadband",
        type=int,
        default=40,
        help="Pixels: no turn if |cx - center| below this",
    )
    parser.add_argument(
        "--init-bbox",
        type=str,
        default="",
        help="Headless: initial box x,y,w,h on resized track frame (after --max-width)",
    )
    parser.add_argument(
        "--serial-port",
        type=str,
        default="",
        help="Override serial port (else env ROBOT_SERIAL_PORT / ARDUINO_SERIAL_PORT)",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Headless: no OpenCV window (no DISPLAY). Requires --init-bbox.",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=30,
        help="With --no-display, print bbox/center every N frames (0=disable)",
    )
    args = parser.parse_args()

    if args.no_display and not args.init_bbox:
        parser.error("--no-display requires --init-bbox (no GUI for selectROI).")

    if args.serial_port:
        os.environ["ROBOT_SERIAL_PORT"] = args.serial_port

    cfg.merge_from_file(args.config)
    cfg.CUDA = torch.cuda.is_available() and cfg.CUDA
    device = torch.device("cuda" if cfg.CUDA else "cpu")

    model = ModelBuilder()
    model.load_state_dict(_load_checkpoint_snapshot(args.snapshot))
    model.eval().to(device)
    tracker = build_tracker(model)

    cap = open_webcam(args.device, args.cap_width, args.cap_height)
    aw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    ah = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    print(f"Webcam opened: device={args.device}, size≈{aw}x{ah}")

    win = "follow"
    if not args.no_display:
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    first = True
    init_rect = None  # type: Optional[Tuple[int, int, int, int]]
    if args.init_bbox:
        init_rect = parse_bbox(args.init_bbox)

    frame_i = 0
    try:
        while True:
            ok, bgr = cap.read()
            if not ok or bgr is None:
                print("Webcam read failed.")
                break

            small, _ = resize_track(bgr, args.max_width)

            if first:
                if init_rect is not None:
                    tracker.init(small, init_rect)
                else:
                    if args.no_display:
                        print("selectROI unavailable with --no-display.")
                        break
                    try:
                        r = cv2.selectROI(win, small, False, False)
                    except cv2.error:
                        print("selectROI failed; use --init-bbox for headless.")
                        break
                    if r[2] <= 1 or r[3] <= 1:
                        print("Empty ROI, exit.")
                        break
                    tracker.init(small, r)
                first = False
                if not args.no_display:
                    cv2.imshow(win, small)
                    if cv2.waitKey(1) == ord("q"):
                        break
                continue

            outputs = tracker.track(small)
            log_cmd = ""
            if "polygon" in outputs:
                polygon = np.array(outputs["polygon"]).astype(np.int32)
                cv2.polylines(
                    small, [polygon.reshape((-1, 1, 2))], True, (0, 255, 0), 2
                )
                log_cmd = "polygon"
            else:
                bbox = list(map(int, outputs["bbox"]))
                x, y, bw, bh = bbox[0], bbox[1], bbox[2], bbox[3]
                cv2.rectangle(small, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
                cx = x + bw / 2.0
                w = small.shape[1]
                h = small.shape[0]
                cv2.line(small, (w // 2, 0), (w // 2, h), (0, 0, 255), 1)

                err = cx - (w / 2.0)
                if abs(err) < args.deadband:
                    comm.forward()
                    log_cmd = "F"
                elif err > 0:
                    comm.right()
                    log_cmd = "R"
                else:
                    comm.left()
                    log_cmd = "L"

            if not args.no_display:
                cv2.imshow(win, small)
                if cv2.waitKey(1) == ord("q"):
                    break
            else:
                frame_i += 1
                if args.log_every > 0 and frame_i % args.log_every == 0:
                    if log_cmd == "polygon":
                        print(f"frame={frame_i} tracker=polygon")
                    elif log_cmd:
                        print(
                            f"frame={frame_i} bbox=({x},{y},{bw},{bh}) "
                            f"cx={cx:.1f} cmd={log_cmd}"
                        )
    finally:
        comm.stop()
        comm.close()
        cap.release()
        if not args.no_display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
