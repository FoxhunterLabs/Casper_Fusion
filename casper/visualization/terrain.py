"""
casper.visualization.terrain
============================

Synthetic terrain generation + IR rendering.

- Terrain is a deterministic pseudo-map
- IR rendering overlays fused position + threat
- Image is dimmed when fusion confidence is low
- Always watermarked: synthetic / non-operational
"""

from typing import Optional

import numpy as np

from casper.models import Telemetry
from casper.presets import AOConfig


class TerrainGenerator:
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate(self, width: int = 80, height: int = 80) -> np.ndarray:
        base = self.rng.normal(0, 1, (height, width))

        # Add grid-like structure
        for i in range(0, width, 8):
            base[i:i + 1, :] += 1.5
            base[:, i:i + 1] += 1.5

        # Add hills
        for _ in range(5):
            cx = self.rng.randint(10, width - 10)
            cy = self.rng.randint(10, height - 10)
            radius = self.rng.randint(5, 15)
            yy, xx = np.ogrid[:height, :width]
            mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius ** 2
            base[mask] += self.rng.uniform(0.5, 2.0)

        return base

    def render_ir(
        self,
        terrain: np.ndarray,
        tel: Telemetry,
        ao: AOConfig,
        fusion_conf: float,
        watermark: str = "SYNTHETIC — NOT OPERATIONAL",
    ) -> np.ndarray:
        img = terrain.copy()
        height, width = img.shape

        # Lat/Lon -> pixel
        x = int(width / 2 + (tel.lon - ao.base_lon) * 600)
        y = int(height / 2 - (tel.lat - ao.base_lat) * 600)
        x = int(np.clip(x, 2, width - 3))
        y = int(np.clip(y, 2, height - 3))

        # Aircraft position
        img[y - 1:y + 2, x - 1:x + 2] += 4.0

        # Threat "heat"
        r = 6 + int(tel.threat_index * 0.12)
        yy, xx = np.ogrid[:height, :width]
        threat_mask = (xx - x) ** 2 + (yy - y) ** 2 <= r * r
        img[threat_mask] += (tel.threat_index / 100.0) * 2.0

        # Normalize
        vmin, vmax = np.percentile(img, 5), np.percentile(img, 95)
        img_norm = np.clip((img - vmin) / (vmax - vmin + 1e-9), 0, 1)

        # Epistemic dimming (lower confidence => darker)
        fusion_conf = float(np.clip(fusion_conf, 0.0, 1.0))
        img_norm *= (1.0 - 0.45 * (1.0 - fusion_conf))

        # RGB
        rgb = np.stack([img_norm] * 3, axis=-1)
        rgb = (rgb * 255).astype(np.uint8)

        # Watermark
        for i, _ in enumerate(watermark):
            px = width - len(watermark) * 2 + i * 2
            py = height - 4
            if 0 <= px < width:
                rgb[py:py + 2, px:px + 2] = 200

        return rgb
