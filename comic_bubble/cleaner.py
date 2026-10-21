"""
comic_bubble.cleaner
~~~~~~~~~~~~~~~~~~~~
Utilities for sampling speech bubble paper color and erasing existing dialogue text
inside drawn manga speech bubbles while preserving bubble borders.
"""

from typing import Tuple
from collections import deque
import numpy as np
from PIL import Image


def sample_bubble_paper_color(
    image: Image.Image,
    box: Tuple[int, int, int, int]
) -> Tuple[int, int, int]:
    """
    Estimate the background paper/fill color of an existing speech bubble within `box`.
    Ignores dark text and border pixels by selecting bright interior pixels (80th percentile).
    """
    rgb = image.convert("RGB")
    w, h = rgb.size
    x1, y1, x2, y2 = box
    x1 = max(0, min(w - 1, int(min(x1, x2))))
    x2 = max(x1 + 1, min(w, int(max(x1, x2))))
    y1 = max(0, min(h - 1, int(min(y1, y2))))
    y2 = max(y1 + 1, min(h, int(max(y1, y2))))

    crop = np.asarray(rgb.crop((x1, y1, x2, y2)), dtype=np.float32)
    if crop.size == 0:
        return (255, 255, 255)

    lum = 0.299 * crop[:, :, 0] + 0.587 * crop[:, :, 1] + 0.114 * crop[:, :, 2]
    p70 = np.percentile(lum, 70)
    p96 = np.percentile(lum, 96)
    mask = (lum >= p70) & (lum <= max(p70 + 1.0, p96))
    if np.any(mask):
        pixels = crop[mask]
    else:
        pixels = crop.reshape(-1, 3)

    med = np.median(pixels, axis=0)
    return (int(np.clip(med[0], 0, 255)), int(np.clip(med[1], 0, 255)), int(np.clip(med[2], 0, 255)))


def clean_bubble_text_in_region(
    image: Image.Image,
    box: Tuple[int, int, int, int]
) -> Tuple[Image.Image, Tuple[int, int, int]]:
    """
    Erase existing dialogue text inside `box = (x1, y1, x2, y2)` on a copy of `image`.
    Preserves outer bubble borders that cross the selection boundary while filling
    interior text characters and their anti-aliased fringes with the detected bubble paper color.

    Returns:
        (cleaned_rgba_image, detected_paper_rgb)
    """
    out_img = image.convert("RGBA").copy()
    w, h = out_img.size
    x1, y1, x2, y2 = box
    x1 = max(0, min(w - 1, int(min(x1, x2))))
    x2 = max(x1 + 1, min(w, int(max(x1, x2))))
    y1 = max(0, min(h - 1, int(min(y1, y2))))
    y2 = max(y1 + 1, min(h, int(max(y1, y2))))

    cw = x2 - x1
    ch = y2 - y1
    if cw < 4 or ch < 4:
        return out_img, (255, 255, 255)

    paper_rgb = sample_bubble_paper_color(out_img, (x1, y1, x2, y2))
    arr = np.asarray(out_img, dtype=np.uint8).copy()
    region = arr[y1:y2, x1:x2, :3].astype(np.float32)

    paper_vec = np.array(paper_rgb, dtype=np.float32).reshape(1, 1, 3)
    color_dist = np.sqrt(np.sum((region - paper_vec) ** 2, axis=2))

    # Ink pixels (text or border lines) differ noticeably from the paper background
    ink_mask = color_dist > 28.0

    # Identify ink connected to the outer boundary of the selection box
    # so we don't accidentally erase the speech bubble's outline frame if the user dragged across it.
    border_connected = np.zeros((ch, cw), dtype=bool)
    q = deque()

    for x in range(cw):
        if ink_mask[0, x]:
            border_connected[0, x] = True
            q.append((0, x))
        if ink_mask[ch - 1, x]:
            border_connected[ch - 1, x] = True
            q.append((ch - 1, x))
    for y in range(ch):
        if ink_mask[y, 0] and not border_connected[y, 0]:
            border_connected[y, 0] = True
            q.append((y, 0))
        if ink_mask[y, cw - 1] and not border_connected[y, cw - 1]:
            border_connected[y, cw - 1] = True
            q.append((y, cw - 1))

    while q:
        cy_i, cx_i = q.popleft()
        for ny_i, nx_i in ((cy_i - 1, cx_i), (cy_i + 1, cx_i), (cy_i, cx_i - 1), (cy_i, cx_i + 1)):
            if 0 <= ny_i < ch and 0 <= nx_i < cw:
                if ink_mask[ny_i, nx_i] and not border_connected[ny_i, nx_i]:
                    border_connected[ny_i, nx_i] = True
                    q.append((ny_i, nx_i))

    # Interior text ink = ink that does NOT connect to the selection boundary
    # (Fallback: if all ink touched the boundary because user dragged tightly inside text, erase all ink)
    text_mask = ink_mask & (~border_connected)
    if not np.any(text_mask) and np.any(ink_mask):
        text_mask = ink_mask

    # Dilate text_mask by 2 pixels to remove anti-aliased gray/halftone fringes around characters
    dilated = text_mask.copy()
    for _ in range(2):
        padded = np.pad(dilated, 1, mode="constant", constant_values=False)
        dilated = (
            padded[1:-1, 1:-1]
            | padded[:-2, 1:-1]
            | padded[2:, 1:-1]
            | padded[1:-1, :-2]
            | padded[1:-1, 2:]
            | padded[:-2, :-2]
            | padded[:-2, 2:]
            | padded[2:, :-2]
            | padded[2:, 2:]
        )
        # Never dilate over protected bubble borders
        dilated = dilated & (~border_connected)

    # Apply paper color to erased text pixels
    for c_idx in range(3):
        channel = arr[y1:y2, x1:x2, c_idx]
        channel[dilated] = paper_rgb[c_idx]
        arr[y1:y2, x1:x2, c_idx] = channel
    arr[y1:y2, x1:x2, 3] = 255

    return Image.fromarray(arr, mode="RGBA"), paper_rgb
