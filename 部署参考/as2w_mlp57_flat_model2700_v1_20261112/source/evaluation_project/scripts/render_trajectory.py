#!/usr/bin/env python3
"""Render recorded native PhysX poses with the training URDF's visual meshes.

MuJoCo is used only for forward kinematics and drawing. No dynamics or policy
inference is run, and the recorded poses are never modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("evaluation", type=Path, help="Directory with summary.json and trajectory.npz")
parser.add_argument("--gpu", type=int, default=1, help="Physical EGL rendering device")
parser.add_argument("--output", type=Path)
args = parser.parse_args()
os.environ["MUJOCO_GL"] = "egl"
os.environ["MUJOCO_EGL_DEVICE_ID"] = str(args.gpu)
os.environ.setdefault("OMP_NUM_THREADS", "2")
sys.path.insert(0, str(ROOT / "tools/render_deps"))

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def origin_attributes(element):
    if element is None:
        return {}
    roll, pitch, yaw = map(float, element.get("rpy", "0 0 0").split())
    cr, cp, cy = (math.cos(a / 2) for a in (roll, pitch, yaw))
    sr, sp, sy = (math.sin(a / 2) for a in (roll, pitch, yaw))
    quat = (cr*cp*cy+sr*sp*sy, sr*cp*cy-cr*sp*sy,
            cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy)
    return {"pos": element.get("xyz", "0 0 0"), "quat": " ".join(map(str, quat))}


def visual_model(urdf_path, cache):
    """Preserve the native URDF's link transforms, joint axes and visual poses."""
    source = ET.parse(urdf_path).getroot()
    links = {link.get("name"): link for link in source.findall("link")}
    children = {}
    for joint in source.findall("joint"):
        children.setdefault(joint.find("parent").get("link"), []).append(joint)
    root = ET.Element("mujoco", model="AS2W recorded PhysX trajectory")
    ET.SubElement(root, "compiler", angle="radian", fusestatic="false")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="480", offheight="264")
    ET.SubElement(visual, "headlight", ambient="0.45 0.45 0.45", diffuse="0.7 0.7 0.7")
    asset = ET.SubElement(root, "asset")
    ET.SubElement(asset, "texture", name="grid", type="2d", builtin="checker", width="512", height="512",
                  rgb1="0.25 0.30 0.35", rgb2="0.36 0.41 0.46")
    ET.SubElement(asset, "material", name="ground", texture="grid", texrepeat="2 2", texuniform="true")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "geom", type="plane", size="0 0 0.01", material="ground")
    ET.SubElement(world, "light", pos="0 -2 5", dir="0 0 -1", directional="true")

    def add_link(name, parent, joint=None):
        attrs = origin_attributes(joint.find("origin")) if joint is not None else {}
        body = ET.SubElement(parent, "body", name=name, **attrs)
        # Masses are placeholders for rendering, never used for dynamics.
        ET.SubElement(body, "inertial", pos="0 0 0", mass="1", diaginertia="0.01 0.01 0.01")
        if joint is None:
            ET.SubElement(body, "freejoint", name="recorded_root")
        elif joint.get("type") != "fixed":
            if joint.get("type") not in {"revolute", "continuous"}:
                raise ValueError(f"Unsupported joint: {joint.attrib}")
            ET.SubElement(body, "joint", name=joint.get("name"), type="hinge",
                          axis=joint.find("axis").get("xyz"), limited="false")
        for index, v in enumerate(links[name].findall("visual")):
            mesh = v.find("geometry/mesh")
            if mesh is None:
                raise ValueError("Expected mesh visuals in the pinned AS2W URDF")
            mesh_path = urdf_path.parent / mesh.get("filename")
            converted = cache / f"{mesh_path.stem}.obj"
            if not converted.exists():
                scene = trimesh.load(str(mesh_path), force="scene")
                geometry = scene.to_geometry()
                if max(geometry.extents) > 3 or not np.isfinite(geometry.vertices).all():
                    raise ValueError(f"Unexpected mesh units or vertices: {mesh_path}")
                geometry.export(str(converted))
            mesh_name = f"{name}_{index}"
            ET.SubElement(asset, "mesh", name=mesh_name, file=str(converted.resolve()),
                          scale=mesh.get("scale", "1 1 1"))
            color = "0.17 0.19 0.21 1" if ("foot" in name or "calf" in name) else "0.70 0.73 0.76 1"
            ET.SubElement(body, "geom", type="mesh", mesh=mesh_name, rgba=color,
                          contype="0", conaffinity="0", **origin_attributes(v.find("origin")))
        for child in children.get(name, []):
            add_link(child.find("child").get("link"), body, child)

    add_link("base_link", world)
    xml = cache / "render_only.xml"
    ET.ElementTree(root).write(xml, encoding="unicode")
    return mujoco.MjModel.from_xml_path(str(xml))


def main():
    evaluation = args.evaluation.resolve()
    summary = json.loads((evaluation / "summary.json").read_text())
    trajectory_path = evaluation / "trajectory.npz"
    data = np.load(trajectory_path)
    names = list(summary["profiles"])
    if len(names) != 8 or data["position"].shape[1:] != (8, 3):
        raise ValueError("Expected the eight-profile native evaluation")
    for key in data.files:
        if not np.isfinite(data[key]).all():
            raise ValueError(f"Nonfinite recorded data: {key}")
    dt = float(np.median(np.diff(data["time"])))
    if not np.isclose(dt, 0.02):
        raise ValueError(f"Expected 50 Hz trajectory, got dt={dt}")
    policy_metadata_path = Path(summary["policy_path"]).with_suffix(".json")
    policy_metadata = json.loads(policy_metadata_path.read_text()) if policy_metadata_path.exists() else {}
    label = (f"model_{policy_metadata['saved_update_index']}" if "saved_update_index" in policy_metadata
             else Path(summary["policy_path"]).stem)
    output = (args.output or evaluation.parent / f"video/as2w_{label}_all_profiles.mp4").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = output.parent / "visual_meshes"
    cache.mkdir(exist_ok=True)
    urdf = ROOT / "assets/as2w/source/as2w.urdf"
    model = visual_model(urdf, cache)
    sim = mujoco.MjData(model)
    joint_ids = np.array([mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
                          for name in summary["joint_names"]])
    if (joint_ids < 0).any() or len(set(joint_ids)) != 16 or model.nq != 23:
        raise ValueError("Recorded/native URDF joint mapping mismatch")
    qids = model.jnt_qposadr[joint_ids]
    renderer = mujoco.Renderer(model, width=480, height=264)
    camera = mujoco.MjvCamera()
    camera.distance, camera.azimuth, camera.elevation = 1.65, 130, -23
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = ImageFont.truetype(font_path, 17)
    title = ImageFont.truetype(font_path, 25)
    chinese = ImageFont.truetype("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", 22)
    labels = {"stand": "静止", "forward": "前进", "backward": "后退", "left": "左移", "right": "右移",
              "turn_left": "左转", "turn_right": "右转", "arc_left": "左弧线"}
    fps, width, height = 25, 1920, 784
    frame_ids = list(range(0, len(data["time"]), 2))
    stderr_path = output.with_suffix(".ffmpeg.log")
    encoder = None
    try:
        with stderr_path.open("w") as errors:
            encoder = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "pipe:0",
                "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-threads", "2",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)], stdin=subprocess.PIPE, stderr=errors)
            for frame_number, step in enumerate(frame_ids):
                frame = Image.new("RGB", (width, height), (15, 22, 32))
                draw = ImageDraw.Draw(frame)
                t = float(data["time"][step])
                draw.text((20, 9), f"AS2W | {label} | recorded PhysX evaluation | 1x speed", font=title, fill="white")
                draw.text((1540, 13), f"t = {t:05.2f} s / 12.00 s", font=font, fill=(105, 210, 235))
                for index, name in enumerate(names):
                    x, y = (index % 4) * 480, 48 + (index // 4) * 352
                    sim.qpos[:3] = data["position"][step, index]
                    sim.qpos[3:7] = data["quaternion"][step, index]
                    sim.qpos[qids] = data["joint_pos"][step, index]
                    mujoco.mj_forward(model, sim)
                    camera.lookat[:] = sim.qpos[:3] + (0, 0, -0.12)
                    renderer.update_scene(sim, camera)
                    frame.paste(Image.fromarray(renderer.render()), (x, y+32))
                    draw.text((x+10, y+2), labels[name], font=chinese, fill=(235, 240, 247))
                    command = data["command"][step, index]
                    actual = (*data["velocity_body"][step, index, :2], data["angular_velocity_body"][step, index, 2])
                    draw.text((x+10, y+301), "cmd: " + " / ".join(f"{v:+.2f}" for v in command), font=font, fill=(105, 210, 235))
                    draw.text((x+10, y+325), "act:  " + " / ".join(f"{v:+.2f}" for v in actual), font=font, fill=(249, 208, 123))
                draw.text((20, 758), "vx / vy [m/s] / wz [rad/s] | 2 s settle + 10 s command | saved poses; no new dynamics | native URDF meshes, simplified colors", font=font, fill=(180, 192, 205))
                if frame_number == 0:
                    frame.save(output.with_suffix(".first_frame.png"))
                if step == 300:
                    frame.save(output.with_suffix(".preview.png"))
                encoder.stdin.write(frame.tobytes())
                if frame_number % 50 == 0:
                    print(f"Rendered {frame_number}/{len(frame_ids)} frames", flush=True)
            encoder.stdin.close()
            if encoder.wait() != 0:
                raise RuntimeError(f"Video encoding failed: {stderr_path}")
    finally:
        if encoder and encoder.poll() is None:
            encoder.stdin.close()
            encoder.wait(timeout=30)
        renderer.close()
    metadata = {"video": str(output), "fps": fps, "frames": len(frame_ids), "duration_seconds": len(frame_ids)/fps,
        "trajectory": str(trajectory_path), "trajectory_sha256": digest(trajectory_path),
        "policy_path": summary["policy_path"], "policy_sha256": summary["policy_sha256"],
        "policy_metadata": policy_metadata, "mujoco_version": mujoco.__version__, "trimesh_version": trimesh.__version__,
        "urdf": str(urdf), "urdf_sha256": digest(urdf), "profiles": names,
        "scope": "Recorded native PhysX root/joint poses, rendered offline at 1x speed. MuJoCo used only for forward kinematics and rendering; no mj_step, policy inference or new dynamics. Native training URDF visual meshes with simplified colors. Not a live screen capture."}
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    main()
