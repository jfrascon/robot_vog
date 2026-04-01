#!/usr/bin/env python3
"""Generate an STL from the side/top-view sheet-metal description."""

from __future__ import annotations

import argparse
import struct
from datetime import datetime
from pathlib import Path
from typing import Sequence

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]


def v_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def v_dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_len(a: Vec3) -> float:
    return (a[0] ** 2 + a[1] ** 2 + a[2] ** 2) ** 0.5


def v_norm(a: Vec3) -> Vec3:
    length = v_len(a)
    if length == 0.0:
        return (0.0, 0.0, 0.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def triangle_normal(tri: Triangle) -> Vec3:
    a, b, c = tri
    return v_norm(v_cross(v_sub(b, a), v_sub(c, a)))


def polygon_area_2d(points: Sequence[Vec2]) -> float:
    area = 0.0
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        area += p[0] * q[1] - q[0] * p[1]
    return 0.5 * area


def cross2d(o: Vec2, a: Vec2, b: Vec2) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def point_in_triangle_2d(p: Vec2, a: Vec2, b: Vec2, c: Vec2) -> bool:
    c1 = cross2d(a, b, p)
    c2 = cross2d(b, c, p)
    c3 = cross2d(c, a, p)
    has_neg = c1 < 0.0 or c2 < 0.0 or c3 < 0.0
    has_pos = c1 > 0.0 or c2 > 0.0 or c3 > 0.0
    return not (has_neg and has_pos)


def project_to_2d(points: Sequence[Vec3]) -> list[Vec2]:
    nx = ny = nz = 0.0
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        nx += (p[1] - q[1]) * (p[2] + q[2])
        ny += (p[2] - q[2]) * (p[0] + q[0])
        nz += (p[0] - q[0]) * (p[1] + q[1])
    ax, ay, az = abs(nx), abs(ny), abs(nz)
    if ax >= ay and ax >= az:
        return [(p[1], p[2]) for p in points]  # project to YZ
    if ay >= ax and ay >= az:
        return [(p[0], p[2]) for p in points]  # project to XZ
    return [(p[0], p[1]) for p in points]  # project to XY


def triangulate_polygon(points: Sequence[Vec3]) -> list[tuple[int, int, int]]:
    if len(points) < 3:
        raise ValueError('Need at least 3 points to triangulate')
    points_2d = project_to_2d(points)
    indices = list(range(len(points_2d)))
    ordered_2d = [points_2d[i] for i in indices]
    if polygon_area_2d(ordered_2d) < 0.0:
        indices.reverse()

    triangles: list[tuple[int, int, int]] = []
    guard = 0
    while len(indices) > 3 and guard < 10_000:
        guard += 1
        ear_found = False
        for k in range(len(indices)):
            i_prev = indices[k - 1]
            i_curr = indices[k]
            i_next = indices[(k + 1) % len(indices)]

            a = points_2d[i_prev]
            b = points_2d[i_curr]
            c = points_2d[i_next]
            if cross2d(a, b, c) <= 1e-12:
                continue

            contains_point = False
            for j in indices:
                if j in (i_prev, i_curr, i_next):
                    continue
                if point_in_triangle_2d(points_2d[j], a, b, c):
                    contains_point = True
                    break
            if contains_point:
                continue

            triangles.append((i_prev, i_curr, i_next))
            del indices[k]
            ear_found = True
            break

        if not ear_found:
            break

    if len(indices) == 3:
        triangles.append((indices[0], indices[1], indices[2]))
    if not triangles:
        raise ValueError('Failed to triangulate polygon')
    return triangles


def orient_outward(tri: Triangle, center: Vec3) -> Triangle:
    a, b, c = tri
    n = triangle_normal(tri)
    tri_center = v_scale(v_add(v_add(a, b), c), 1.0 / 3.0)
    if v_dot(n, v_sub(tri_center, center)) < 0.0:
        return (a, c, b)
    return tri


def extrude_polygon_one_sided(polygon: Sequence[Vec3], offset: Vec3) -> list[Triangle]:
    side_a = list(polygon)
    side_b = [v_add(p, offset) for p in polygon]
    all_vertices = side_a + side_b
    center = (
        sum(p[0] for p in all_vertices) / len(all_vertices),
        sum(p[1] for p in all_vertices) / len(all_vertices),
        sum(p[2] for p in all_vertices) / len(all_vertices),
    )

    triangles: list[Triangle] = []
    cap_tris = triangulate_polygon(polygon)
    for i, j, k in cap_tris:
        triangles.append((side_a[i], side_a[j], side_a[k]))
        triangles.append((side_b[i], side_b[k], side_b[j]))

    for i in range(len(polygon)):
        j = (i + 1) % len(polygon)
        a0, a1 = side_a[i], side_a[j]
        b1, b0 = side_b[j], side_b[i]
        triangles.append((a0, a1, b1))
        triangles.append((a0, b1, b0))

    return [orient_outward(t, center) for t in triangles]


def interior_normal_for_edge(polygon_xz: Sequence[Vec2], edge_index: int) -> tuple[float, float]:
    area = polygon_area_2d(polygon_xz)
    i = edge_index
    j = (i + 1) % len(polygon_xz)
    x1, z1 = polygon_xz[i]
    x2, z2 = polygon_xz[j]
    dx = x2 - x1
    dz = z2 - z1

    # For CCW contours, interior is on the left side of each edge.
    # For CW contours, interior is on the right side.
    if area >= 0.0:
        nx, nz = (-dz, dx)
    else:
        nx, nz = (dz, -dx)
    length = (nx**2 + nz**2) ** 0.5
    if length == 0.0:
        raise ValueError('Degenerate edge with zero length')
    return (nx / length, nz / length)


def write_binary_stl(path: Path, triangles: Sequence[Triangle], name: str = 'sheet_body') -> None:
    header = name.encode('ascii', errors='ignore')[:80]
    header = header + b'\0' * (80 - len(header))
    with path.open('wb') as fh:
        fh.write(header)
        fh.write(struct.pack('<I', len(triangles)))
        for tri in triangles:
            n = triangle_normal(tri)
            fh.write(struct.pack('<3f', *n))
            for v in tri:
                fh.write(struct.pack('<3f', *v))
            fh.write(struct.pack('<H', 0))


def build_model(thickness_m: float) -> list[Triangle]:
    triangles: list[Triangle] = []

    side_profile = [(-0.7655, 0.82), (0.11, 0.82), (0.11, 0.0), (0.7655, -0.41), (0.7655, -0.82), (-0.7655, -0.82)]

    y_outer_right = -0.3870
    y_inner_right = -0.3850
    y_outer_left = 0.3870
    y_inner_left = 0.3850

    # Lateral sheet plates: given points are the exterior face, thickness goes inward.
    right_outer = [(x, y_outer_right, z) for x, z in side_profile]
    left_outer = [(x, y_outer_left, z) for x, z in side_profile]
    triangles.extend(extrude_polygon_one_sided(right_outer, (0.0, thickness_m, 0.0)))
    triangles.extend(extrude_polygon_one_sided(left_outer, (0.0, -thickness_m, 0.0)))

    # Closing plates from contour edges, except bottom and rear full-height.
    # Edge indices for side_profile:
    # 0: top, 1: front vertical, 2: inclined, 3: front-lower vertical, 4: bottom, 5: rear vertical
    closing_edges = (0, 1, 2, 3)
    for i in closing_edges:
        j = (i + 1) % len(side_profile)
        x1, z1 = side_profile[i]
        x2, z2 = side_profile[j]
        plate_outer = [(x1, y_inner_left, z1), (x2, y_inner_left, z2), (x2, y_inner_right, z2), (x1, y_inner_right, z1)]
        nx, nz = interior_normal_for_edge(side_profile, i)
        triangles.extend(extrude_polygon_one_sided(plate_outer, (nx * thickness_m, 0.0, nz * thickness_m)))

    # Rear plate only on upper half: z in [0.0, 0.82], open below z=0.
    rear_upper_outer = [
        (-0.7655, y_inner_left, 0.82),
        (-0.7655, y_inner_right, 0.82),
        (-0.7655, y_inner_right, 0.0),
        (-0.7655, y_inner_left, 0.0),
    ]
    triangles.extend(extrude_polygon_one_sided(rear_upper_outer, (thickness_m, 0.0, 0.0)))

    return triangles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate STL from top+side views.')
    parser.add_argument(
        '--output', type=Path, default=Path(f'agr_4sw_base_{datetime.now():%Y%m%d}.stl'), help='Output STL file path.'
    )
    parser.add_argument(
        '--thickness-mm', type=float, default=2.0, help='Sheet thickness in millimeters (default: 2.0).'
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    thickness_m = args.thickness_mm / 1000.0
    triangles = build_model(thickness_m)
    write_binary_stl(args.output, triangles)
    print(f'Wrote {args.output} with {len(triangles)} triangles (thickness={args.thickness_mm:.3f} mm).')


if __name__ == '__main__':
    main()
