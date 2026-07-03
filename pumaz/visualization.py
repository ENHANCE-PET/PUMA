"""Visualization exports for PUMA RGB multiplexed PET volumes."""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Sequence

import cv2
import nibabel as nib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def strip_nii_suffix(path: str | Path) -> str:
    name = Path(path).name
    if name.endswith(".nii.gz"):
        return name[:-7]
    if name.endswith(".nii"):
        return name[:-4]
    return Path(path).stem


def load_rgb_nifti(path: str | Path) -> tuple[np.ndarray, tuple[float, float, float], np.ndarray]:
    image = nib.load(str(path))
    data = np.asanyarray(image.dataobj)
    if data.dtype.fields and {"R", "G", "B"}.issubset(data.dtype.fields):
        rgb = data.view(("u1", 3)).reshape(image.shape + (3,))
    elif data.ndim == 4 and data.shape[-1] == 3:
        rgb = data
    else:
        raise ValueError(f"{path} is not an RGB NIfTI volume.")
    spacing = tuple(float(value) for value in image.header.get_zooms()[:3])
    return np.ascontiguousarray(rgb.astype(np.uint8, copy=False)), spacing, image.affine


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _add_glow(image: Image.Image, strength: float, radius: float = 7.0) -> Image.Image:
    if strength <= 0:
        return image
    base = np.asarray(image).astype(np.float32)
    glow = np.asarray(image.filter(ImageFilter.GaussianBlur(radius=radius))).astype(np.float32)
    return Image.fromarray(np.clip(base + glow * strength, 0, 255).astype(np.uint8), mode="RGB")


def _crop_panel(panel: np.ndarray, pad: int = 18) -> np.ndarray:
    mask = panel.max(axis=2) > 3
    coordinates = np.argwhere(mask)
    if coordinates.size == 0:
        return panel
    y0, x0 = coordinates.min(axis=0)
    y1, x1 = coordinates.max(axis=0) + 1
    return panel[
        max(0, y0 - pad): min(panel.shape[0], y1 + pad),
        max(0, x0 - pad): min(panel.shape[1], x1 + pad),
    ]


def _fit_panel(
    panel: np.ndarray,
    target_height: int,
    glow: float,
    row_spacing: float = 1.0,
    col_spacing: float = 1.0,
) -> Image.Image:
    image = Image.fromarray(_crop_panel(panel), mode="RGB")
    image = _add_glow(image, glow)
    physical_height = image.height * row_spacing
    physical_width = image.width * col_spacing
    target_width = max(1, int(round(target_height * physical_width / physical_height)))
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def save_mip_png(
    rgb_nifti: str | Path,
    output_png: str | Path,
    title: str = "PUMA multiplex MIP",
    glow: float = 0.22,
) -> None:
    rgb, spacing, affine = load_rgb_nifti(rgb_nifti)
    flip_vertical = _should_flip_vertical(affine)
    coronal = rgb.max(axis=1).transpose(1, 0, 2)
    sagittal = rgb.max(axis=0).transpose(1, 0, 2)
    if flip_vertical:
        coronal = coronal[::-1, :, :]
        sagittal = sagittal[::-1, :, :]
    axial = np.rot90(rgb.max(axis=2), 1)
    panels = [
        ("Coronal MIP", _fit_panel(coronal, 980, glow, spacing[2], spacing[0])),
        ("Sagittal MIP", _fit_panel(sagittal, 980, glow, spacing[2], spacing[1])),
        ("Axial MIP", _fit_panel(axial, 520, glow, spacing[1], spacing[0])),
    ]

    margin = 42
    gap = 34
    title_h = 92
    footer_h = 56
    label_h = 38
    content_h = max(panel.height for _, panel in panels) + label_h
    content_w = sum(panel.width for _, panel in panels) + gap * (len(panels) - 1)
    canvas = Image.new("RGB", (content_w + margin * 2, title_h + content_h + footer_h), (0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(34)
    label_font = _load_font(20)

    draw.text((margin, 28), title, font=title_font, fill=(235, 235, 235))
    x = margin
    y = title_h
    for label, panel in panels:
        canvas.paste(panel, (x, y))
        bbox = draw.textbbox((0, 0), label, font=label_font)
        draw.text((x + (panel.width - (bbox[2] - bbox[0])) // 2, y + panel.height + 10),
                  label, font=label_font, fill=(190, 190, 190))
        x += panel.width + gap

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_png)


def save_gallery_png(preset_pngs: Sequence[tuple[str, str | Path]], output_png: str | Path) -> None:
    thumb_w = 1100
    thumb_h = 581
    pad = 34
    label_h = 54
    columns = 2
    rows = math.ceil(len(preset_pngs) / columns)
    label_font = _load_font(28)
    canvas = Image.new(
        "RGB",
        (thumb_w * columns + pad * (columns + 1), rows * (thumb_h + label_h) + pad * (rows + 1)),
        (0, 0, 0),
    )
    draw = ImageDraw.Draw(canvas)

    for index, (label, path) in enumerate(preset_pngs):
        image = Image.open(path).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = pad + (index % columns) * (thumb_w + pad)
        y = pad + (index // columns) * (thumb_h + label_h + pad)
        canvas.paste(image, (x, y))
        draw.text((x, y + thumb_h + 12), label, font=label_font, fill=(230, 230, 230))

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_png)


def _should_flip_vertical(affine: np.ndarray) -> bool:
    return bool(affine[:3, 2][2] > 0)


def _rotation_matrix(width: int, height: int, angle: float, pad_rotation: bool) -> tuple[np.ndarray, tuple[int, int]]:
    if pad_rotation:
        out_width = int(math.ceil(math.sqrt(width * width + height * height)))
        out_height = out_width
    else:
        out_width = width
        out_height = height
    center = ((width - 1) / 2.0, (height - 1) / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    matrix[0, 2] += (out_width - width) / 2.0
    matrix[1, 2] += (out_height - height) / 2.0
    return matrix, (out_width, out_height)


def _render_projection(
    rgb: np.ndarray,
    angle: float,
    interpolation: int,
    pad_rotation: bool,
    flip_vertical: bool,
) -> np.ndarray:
    height, width, depth, _ = rgb.shape
    matrix, output_size = _rotation_matrix(width, height, angle, pad_rotation)
    output_width, output_height = output_size
    projection = np.empty((depth, output_width, 3), dtype=np.uint8)
    for zi in range(depth):
        rotated = cv2.warpAffine(
            rgb[:, :, zi, :],
            matrix,
            (output_width, output_height),
            flags=interpolation,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )
        projection[zi, :, :] = rotated.max(axis=0)
    if flip_vertical:
        return projection[::-1, :, :]
    return projection


def _global_crop(frames: Sequence[np.ndarray], threshold: int, pad: int) -> tuple[slice, slice]:
    mask = np.zeros(frames[0].shape[:2], dtype=bool)
    for frame in frames:
        mask |= frame.max(axis=2) > threshold
    coordinates = np.argwhere(mask)
    if coordinates.size == 0:
        return slice(None), slice(None)
    y0, x0 = coordinates.min(axis=0)
    y1, x1 = coordinates.max(axis=0) + 1
    return (
        slice(max(0, y0 - pad), min(mask.shape[0], y1 + pad)),
        slice(max(0, x0 - pad), min(mask.shape[1], x1 + pad)),
    )


def _even(value: int) -> int:
    return value if value % 2 == 0 else value + 1


def _resize_physical(frame: np.ndarray, spacing_x: float, spacing_z: float, width: int, glow: float) -> Image.Image:
    height_px, width_px = frame.shape[:2]
    width_mm = width_px * spacing_x
    height_mm = height_px * spacing_z
    target_width = _even(width)
    target_height = _even(int(round(target_width * height_mm / width_mm)))
    image = _add_glow(Image.fromarray(frame, mode="RGB"), glow, radius=5.0)
    return image.resize((target_width, target_height), Image.Resampling.LANCZOS)


def _open_video_writer(path: Path, frame_size: tuple[int, int], fps: float) -> cv2.VideoWriter:
    for codec in ("avc1", "H264", "mp4v"):
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, frame_size)
        if writer.isOpened():
            return writer
    raise RuntimeError("Could not open an MP4 writer. Check the OpenCV video codec installation.")


def render_rotating_mip_mp4(
    rgb_nifti: str | Path,
    output_mp4: str | Path,
    frames: int = 120,
    fps: float = 24.0,
    width: int = 1600,
    interpolation: str = "cubic",
    glow: float = 0.08,
    crop_threshold: int = 3,
    crop_pad: int = 18,
) -> Path:
    if frames <= 0:
        raise ValueError("frames must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")
    if width <= 0:
        raise ValueError("width must be positive")

    interpolation_map = {
        "nearest": cv2.INTER_NEAREST,
        "linear": cv2.INTER_LINEAR,
        "cubic": cv2.INTER_CUBIC,
    }
    if interpolation not in interpolation_map:
        raise ValueError("interpolation must be nearest, linear, or cubic")

    t0 = time.perf_counter()
    rgb, spacing, affine = load_rgb_nifti(rgb_nifti)
    flip_vertical = _should_flip_vertical(affine)
    angles = [360.0 * index / frames for index in range(frames)]

    t_render = time.perf_counter()
    projections = [
        _render_projection(rgb, angle, interpolation_map[interpolation], True, flip_vertical)
        for angle in angles
    ]
    render_seconds = time.perf_counter() - t_render

    z_crop, x_crop = _global_crop(projections, crop_threshold, crop_pad)
    first_frame = _resize_physical(projections[0][z_crop, x_crop, :], spacing[0], spacing[2], width, glow)

    output_mp4 = Path(output_mp4)
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    writer = _open_video_writer(output_mp4, first_frame.size, fps)

    t_encode = time.perf_counter()
    for projection in projections:
        frame = _resize_physical(projection[z_crop, x_crop, :], spacing[0], spacing[2], width, glow)
        writer.write(cv2.cvtColor(np.asarray(frame), cv2.COLOR_RGB2BGR))
    writer.release()
    encode_seconds = time.perf_counter() - t_encode

    report = {
        "input": str(rgb_nifti),
        "output": str(output_mp4),
        "shape": list(rgb.shape),
        "spacing_mm": list(spacing),
        "frames": frames,
        "fps": fps,
        "width": width,
        "frame_size": list(first_frame.size),
        "interpolation": interpolation,
        "flip_vertical": flip_vertical,
        "crop_z": [None if z_crop.start is None else int(z_crop.start),
                   None if z_crop.stop is None else int(z_crop.stop)],
        "crop_x": [None if x_crop.start is None else int(x_crop.start),
                   None if x_crop.stop is None else int(x_crop.stop)],
        "render_seconds": render_seconds,
        "encode_seconds": encode_seconds,
        "total_seconds": time.perf_counter() - t0,
    }
    output_mp4.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_mp4
