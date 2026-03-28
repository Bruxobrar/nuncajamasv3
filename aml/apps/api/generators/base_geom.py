import math


Triangle = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


def polar(radius: float, theta: float, z: float) -> tuple[float, float, float]:
    return (radius * math.cos(theta), radius * math.sin(theta), z)


def superellipse(rx: float, ry: float, theta: float, z: float, exponent: float = 4.0) -> tuple[float, float, float]:
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    x = math.copysign(abs(cos_t) ** (2.0 / exponent), cos_t) * rx
    y = math.copysign(abs(sin_t) ** (2.0 / exponent), sin_t) * ry
    return (x, y, z)


def add_quad(tris: list[Triangle], v00, v10, v11, v01, flip: bool = False):
    if not flip:
        tris.append((v00, v10, v11))
        tris.append((v00, v11, v01))
    else:
        tris.append((v00, v11, v10))
        tris.append((v00, v01, v11))


def add_box(tris: list[Triangle], x0: float, x1: float, y0: float, y1: float, z0: float, z1: float):
    p000 = (x0, y0, z0)
    p001 = (x0, y0, z1)
    p010 = (x0, y1, z0)
    p011 = (x0, y1, z1)
    p100 = (x1, y0, z0)
    p101 = (x1, y0, z1)
    p110 = (x1, y1, z0)
    p111 = (x1, y1, z1)
    add_quad(tris, p000, p100, p110, p010)
    add_quad(tris, p001, p011, p111, p101)
    add_quad(tris, p000, p001, p101, p100)
    add_quad(tris, p010, p110, p111, p011)
    add_quad(tris, p000, p010, p011, p001)
    add_quad(tris, p100, p101, p111, p110)


def add_capped_ring(tris: list[Triangle], r_in: float, r_out: float, z0: float, z1: float, n_theta: int):
    for index in range(n_theta):
        t0 = (2.0 * math.pi * index) / n_theta
        t1 = (2.0 * math.pi * (index + 1)) / n_theta
        o00 = polar(r_out, t0, z0)
        o01 = polar(r_out, t1, z0)
        o10 = polar(r_out, t0, z1)
        o11 = polar(r_out, t1, z1)
        add_quad(tris, o00, o10, o11, o01)

        if r_in > 0.0:
            i00 = polar(r_in, t0, z0)
            i01 = polar(r_in, t1, z0)
            i10 = polar(r_in, t0, z1)
            i11 = polar(r_in, t1, z1)
            add_quad(tris, i00, i01, i11, i10)
            add_quad(tris, i00, o00, o01, i01, flip=True)
            add_quad(tris, i10, i11, o11, o10, flip=True)
        else:
            c0 = (0.0, 0.0, z0)
            c1 = (0.0, 0.0, z1)
            tris.append((c0, o01, o00))
            tris.append((c1, o10, o11))


def add_superellipse_ring(
    tris: list[Triangle],
    rx_in: float,
    ry_in: float,
    rx_out: float,
    ry_out: float,
    z0: float,
    z1: float,
    n_theta: int,
    exponent: float = 4.0,
):
    for index in range(n_theta):
        t0 = (2.0 * math.pi * index) / n_theta
        t1 = (2.0 * math.pi * (index + 1)) / n_theta
        o00 = superellipse(rx_out, ry_out, t0, z0, exponent)
        o01 = superellipse(rx_out, ry_out, t1, z0, exponent)
        o10 = superellipse(rx_out, ry_out, t0, z1, exponent)
        o11 = superellipse(rx_out, ry_out, t1, z1, exponent)
        add_quad(tris, o00, o10, o11, o01)

        if rx_in > 0.0 and ry_in > 0.0:
            i00 = superellipse(rx_in, ry_in, t0, z0, exponent)
            i01 = superellipse(rx_in, ry_in, t1, z0, exponent)
            i10 = superellipse(rx_in, ry_in, t0, z1, exponent)
            i11 = superellipse(rx_in, ry_in, t1, z1, exponent)
            add_quad(tris, i00, i01, i11, i10)
            add_quad(tris, i00, o00, o01, i01, flip=True)
            add_quad(tris, i10, i11, o11, o10, flip=True)


def add_wave_ring(
    tris: list[Triangle],
    r_in: float,
    r_out: float,
    z0: float,
    z1: float,
    n_theta: int,
    amp: float,
    lobes: int,
):
    for index in range(n_theta):
        t0 = (2.0 * math.pi * index) / n_theta
        t1 = (2.0 * math.pi * (index + 1)) / n_theta
        ro0 = r_out + math.sin(t0 * lobes) * amp
        ro1 = r_out + math.sin(t1 * lobes) * amp
        ri0 = max(0.0, r_in + math.sin(t0 * lobes) * amp * 0.3)
        ri1 = max(0.0, r_in + math.sin(t1 * lobes) * amp * 0.3)
        o00 = polar(ro0, t0, z0)
        o01 = polar(ro1, t1, z0)
        o10 = polar(ro0, t0, z1)
        o11 = polar(ro1, t1, z1)
        add_quad(tris, o00, o10, o11, o01)
        if r_in > 0.0:
            i00 = polar(ri0, t0, z0)
            i01 = polar(ri1, t1, z0)
            i10 = polar(ri0, t0, z1)
            i11 = polar(ri1, t1, z1)
            add_quad(tris, i00, i01, i11, i10)
            add_quad(tris, i00, o00, o01, i01, flip=True)
            add_quad(tris, i10, i11, o11, o10, flip=True)


def add_lofted_superellipse_ring(
    tris: list[Triangle],
    lower_inner: tuple[float, float],
    lower_outer: tuple[float, float],
    upper_inner: tuple[float, float],
    upper_outer: tuple[float, float],
    z0: float,
    z1: float,
    n_theta: int,
    exponent: float = 4.0,
):
    for index in range(n_theta):
        t0 = (2.0 * math.pi * index) / n_theta
        t1 = (2.0 * math.pi * (index + 1)) / n_theta

        lo00 = superellipse(lower_outer[0], lower_outer[1], t0, z0, exponent)
        lo01 = superellipse(lower_outer[0], lower_outer[1], t1, z0, exponent)
        lo10 = superellipse(upper_outer[0], upper_outer[1], t0, z1, exponent)
        lo11 = superellipse(upper_outer[0], upper_outer[1], t1, z1, exponent)
        add_quad(tris, lo00, lo10, lo11, lo01)

        li00 = superellipse(lower_inner[0], lower_inner[1], t0, z0, exponent)
        li01 = superellipse(lower_inner[0], lower_inner[1], t1, z0, exponent)
        li10 = superellipse(upper_inner[0], upper_inner[1], t0, z1, exponent)
        li11 = superellipse(upper_inner[0], upper_inner[1], t1, z1, exponent)
        add_quad(tris, li00, li01, li11, li10)
        add_quad(tris, li00, lo00, lo01, li01, flip=True)
        add_quad(tris, li10, li11, lo11, lo10, flip=True)
