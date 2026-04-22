import numpy as np
from opensimplex import OpenSimplex


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

    # OpenSimplex accepts the seed directly — same seed always produces
    # the same noise field, satisfying the reproducibility requirement.
    gen = OpenSimplex(seed=seed)

    noise_map = np.empty((height, width), dtype=np.float64)

    # Layer multiple octaves manually to replicate the fractal detail
    # that pnoise2's octaves parameter provided.
    octaves = 6
    persistence = 0.5
    lacunarity = 2.0

    for y in range(height):
        for x in range(width):
            value = 0.0
            amplitude = 1.0
            frequency = 1.0
            for _ in range(octaves):
                nx = x / scale * frequency
                ny = y / scale * frequency
                value += gen.noise2(nx, ny) * amplitude
                amplitude *= persistence
                frequency *= lacunarity
            noise_map[y, x] = value

    # Normalize from the summed octave range to [0, 1]
    min_val = noise_map.min()
    max_val = noise_map.max()

    if max_val == min_val:
        return np.zeros_like(noise_map)

    return (noise_map - min_val) / (max_val - min_val)
