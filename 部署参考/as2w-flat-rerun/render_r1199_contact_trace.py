"""Render recorded R1199 MuJoCo states; no policy execution or hardware I/O."""

import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) != 5:
    raise SystemExit("usage: render_r1199_contact_trace.py ASSETS RUNTIME TRACE.json VIDEO.mp4")

assets, runtime, trace_path, video_path = map(Path, sys.argv[1:])
sys.path.insert(0, str(runtime.resolve()))
import mujoco_screen as sim  # noqa: E402

import mujoco as mj  # noqa: E402

sim.ROOT = assets.resolve()
model = sim.load_flat_model(True, True, seed=0)
data = mj.MjData(model)
trace = json.loads(trace_path.read_text())
states = trace["physics_substeps"]
contact_t = trace["first_nonwheel_over_1n_s"]
assert states and contact_t is not None

# Make the implicated right rear calf visible in the side view.
calf_id = model.body("RR_calf").id
for geom_id in range(model.ngeom):
    if model.geom_bodyid[geom_id] == calf_id:
        model.geom_rgba[geom_id] = [0.9, 0.06, 0.04, 1.0]

width, height, fps = 960, 540, 25
model.vis.global_.offwidth = width
model.vis.global_.offheight = height
cam = mj.MjvCamera()
cam.type = mj.mjtCamera.mjCAMERA_FREE
cam.lookat[:] = [0.20, 0.0, 0.26]
cam.distance = 1.7
cam.azimuth = 90
cam.elevation = -12
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font = ImageFont.truetype(font_path, 23) if Path(font_path).exists() else ImageFont.load_default()
video_path.parent.mkdir(parents=True, exist_ok=True)
encoded_path = Path.home() / video_path.name
cmd = ["/snap/bin/ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
       "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
       "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p", str(encoded_path)]
frames = 0
with mj.Renderer(model, height=height, width=width) as renderer:
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as encoder:
        start, end = trace["window_s"]
        for t in np.arange(start, end, 1.0 / fps):
            row = min(states, key=lambda item: abs(item["t_s"] - t))
            data.qpos[:] = row["qpos"]
            data.qvel[:] = row["qvel"]
            mj.mj_forward(model, data)
            renderer.update_scene(data, camera=cam)
            image = Image.fromarray(renderer.render())
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, width, 74), fill=(15, 20, 27))
            label = "R1199 forward seed 202 | original push" if trace["push_enabled"] else "R1199 forward seed 202 | push disabled"
            draw.text((18, 8), label, font=font, fill=(245, 245, 245))
            touching = [item for item in row["nonwheel"] if item["body"] == "RR_calf"]
            force = max((item["normal_n"] for item in touching), default=0.0)
            line = f"t={row['t_s']:.3f}s   first touch={contact_t:.3f}s   RR_calf={force:.1f}N"
            draw.text((18, 40), line, font=font, fill=(255, 125, 105) if force > 1 else (180, 220, 250))
            if contact_t <= t < contact_t + 1.0 / fps:
                image.save(video_path.with_suffix(".png"))
            try:
                encoder.stdin.write(np.asarray(image).tobytes())
            except BrokenPipeError as exc:
                raise RuntimeError(encoder.stderr.read().decode(errors="replace")) from exc
            frames += 1
        encoder.stdin.close()
        stderr = encoder.stderr.read().decode(errors="replace")
        rc = encoder.wait()
        if rc:
            raise RuntimeError(f"ffmpeg exit {rc}: {stderr}")
shutil.copyfile(encoded_path, video_path)
print(f"rendered {frames} frames to {video_path}")
