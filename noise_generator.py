import numpy as np
from noise import pnoise2


def generate_noise_map(width: int, height: int, scale: float, seed: int) -> np.ndarray:
    """
    Generate a 2D Perlin noise map normalized to [0, 1].

    Args:
        width:  Number of columns in the output grid.
        height: Number of rows in the output grid.
        scale:  Zoom level of the noise pattern. Larger values produce
                smoother, broader features; smaller values produce
                finer, more chaotic detail.
        seed:   Integer seed for reproducibility. Applied as an offset
                into the noise space.

    Returns:
        A (height x width) NumPy float64 array with values in [0, 1].
    """
    if scale <= 0:
        raise ValueError("scale must be greater than 0.")

    rng = np.random.default_rng(seed)
    offset_x = rng.integers(0, 250_000)
    offset_y = rng.integers(0, 250_000)

    noise_map = np.empty((height, width), dtype=np.float64)

    for y in range(height):
        for x in range(width):
            nx = (x + offset_x) / scale
            ny = (y + offset_y) / scale
            noise_map[y, x] = pnoise2(nx, ny, octaves=6, persistence=0.5, lacunarity=2.0)

    # Normalize from pnoise2 range (~[-1, 1]) to [0, 1]
    min_val = noise_map.min()
    max_val = noise_map.max()

    if max_val == min_val:
        return np.zeros_like(noise_map)

    return (noise_map - min_val) / (max_val - min_val)
