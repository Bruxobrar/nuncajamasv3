import argparse
import math
import struct
from dataclasses import dataclass
from typing import List, Tuple

vec3 = Tuple[float, float, float]
tri3 = Tuple[vec3, vec3, vec3]


def vecSub(a: vec3, b: vec3) -> vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vecCross(a: vec3, b: vec3) -> vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vecLen(v: vec3) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def vecNorm(v: vec3) -> vec3:
    l = vecLen(v)
    if l == 0.0:
        return (0.0, 0.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


def triNormal(a: vec3, b: vec3, c: vec3) -> vec3:
    return vecNorm(vecCross(vecSub(b, a), vecSub(c, a)))


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def mix(a: float, b: float, t: float) -> float:
    return a * (1.0 - t) + b * t


def smoothstep(a: float, b: float, x: float) -> float:
    if a == b:
        return 0.0
    t = clamp((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fract(x: float) -> float:
    return x - math.floor(x)


def hash2(a: float, b: float) -> float:
    v = math.sin(a * 127.1 + b * 311.7) * 43758.5453123
    return fract(v)


def valueNoise2(a: float, b: float) -> float:
    ia = math.floor(a)
    ib = math.floor(b)
    fa = a - ia
    fb = b - ib

    va = hash2(ia, ib)
    vb = hash2(ia + 1.0, ib)
    vc = hash2(ia, ib + 1.0)
    vd = hash2(ia + 1.0, ib + 1.0)

    ua = fa * fa * (3.0 - 2.0 * fa)
    ub = fb * fb * (3.0 - 2.0 * fb)

    v1 = mix(va, vb, ua)
    v2 = mix(vc, vd, ua)
    return mix(v1, v2, ub)


def fbm2(a: float, b: float, octaves: int = 5) -> float:
    total = 0.0
    amp = 0.5
    freq = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += valueNoise2(a * freq, b * freq) * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    if norm == 0.0:
        return 0.0
    return total / norm


def sphPoint(radius: float, theta: float, phi: float) -> vec3:
    sinPhi = math.sin(phi)
    return (
        radius * sinPhi * math.cos(theta),
        radius * sinPhi * math.sin(theta),
        radius * math.cos(phi),
    )


def writeBinaryStl(path: str, triangles: List[tri3]) -> None:
    header = b"lampgenPlanet procedural shell".ljust(80, b"\0")
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for a, b, c in triangles:
            n = triNormal(a, b, c)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *a))
            f.write(struct.pack("<3f", *b))
            f.write(struct.pack("<3f", *c))
            f.write(struct.pack("<H", 0))


@dataclass
class lampgenPlanet:
    outputPath: str = "lampgenPlanet.stl"
    worldType: str = "naturalWorld"

    diameter: float = 160.0
    minThickness: float = 1.0
    maxThickness: float = 2.2

    reliefAmount: float = 0.8
    lightAmount: float = 1.0

    thetaSteps: int = 220
    phiSteps: int = 120

    openingDiameter: float = 46.0
    openingFade: float = 10.0

    poleFade: float = 0.25
    seed: float = 0.0


def planetMaskPolar(phi: float, fade: float) -> float:
    u = phi / math.pi
    north = smoothstep(0.0, fade, u)
    south = smoothstep(0.0, fade, 1.0 - u)
    return north * south


def naturalField(theta: float, phi: float, p: lampgenPlanet) -> Tuple[float, float]:
    lon = theta / (2.0 * math.pi)
    lat = phi / math.pi

    baseA = fbm2(lon * 2.7 + 10.0 + p.seed, lat * 2.4 + 5.0 + p.seed, 5)
    baseB = fbm2(lon * 5.3 + 21.0 + p.seed, lat * 4.9 + 8.0 + p.seed, 4)
    baseC = fbm2(lon * 11.0 + 37.0 + p.seed, lat * 10.0 + 13.0 + p.seed, 3)

    landRaw = baseA * 0.68 + baseB * 0.24 + baseC * 0.08
    landMask = smoothstep(0.48, 0.62, landRaw)

    ridgeA = abs(math.sin(theta * 3.0 + phi * 5.5))
    ridgeB = abs(math.sin(theta * 7.0 - phi * 4.0))
    ridgeC = fbm2(lon * 18.0 + 70.0 + p.seed, lat * 18.0 + 33.0 + p.seed, 3)
    ridge = (ridgeA * 0.45 + ridgeB * 0.35 + ridgeC * 0.20)
    ridge = smoothstep(0.62, 0.88, ridge) * landMask

    oceanDetail = fbm2(lon * 8.0 + 90.0 + p.seed, lat * 8.0 + 45.0 + p.seed, 3)
    polar = 1.0 - planetMaskPolar(phi, 0.18)

    relief = (landMask * 0.55 + ridge * 0.45) * planetMaskPolar(phi, p.poleFade)
    relief += polar * 0.08

    light = 0.0
    light += (1.0 - landMask) * (0.58 + oceanDetail * 0.22)
    light += landMask * (0.30 + ridge * 0.10)
    light += polar * 0.20

    relief = clamp(relief, 0.0, 1.0)
    light = clamp(light, 0.0, 1.0)
    return relief, light


def urbanField(theta: float, phi: float, p: lampgenPlanet) -> Tuple[float, float]:
    lon = theta / (2.0 * math.pi)
    lat = phi / math.pi

    bandA = abs(math.sin(theta * 10.0 + phi * 4.5))
    bandB = abs(math.sin(theta * 22.0 - phi * 8.0))
    panel = abs(math.sin(theta * 42.0) * math.sin(phi * 26.0))
    node = fbm2(lon * 16.0 + 120.0 + p.seed, lat * 16.0 + 60.0 + p.seed, 4)

    gridMain = smoothstep(0.86, 0.97, bandA * 0.55 + bandB * 0.45)
    gridFine = smoothstep(0.90, 0.985, panel)
    nodeMask = smoothstep(0.63, 0.82, node)

    equatorBias = math.pow(math.sin(phi), 1.4)
    polesDark = 1.0 - planetMaskPolar(phi, 0.22)

    relief = gridMain * 0.25 + gridFine * 0.20 + nodeMask * 0.18
    relief *= planetMaskPolar(phi, p.poleFade)

    light = 0.0
    light += gridMain * 0.60
    light += gridFine * 0.28
    light += nodeMask * 0.45
    light += equatorBias * 0.18
    light -= polesDark * 0.20

    light = clamp(light, 0.0, 1.0)
    relief = clamp(relief, 0.0, 1.0)
    return relief, light


def sampleField(theta: float, phi: float, p: lampgenPlanet) -> Tuple[float, float]:
    if p.worldType == "urbanWorld":
        return urbanField(theta, phi, p)
    return naturalField(theta, phi, p)


def buildShell(p: lampgenPlanet) -> List[tri3]:
    triangles: List[tri3] = []

    radiusBase = p.diameter * 0.5
    openingRadius = p.openingDiameter * 0.5

    thetaCount = max(24, p.thetaSteps)
    phiCount = max(24, p.phiSteps)

    outerGrid: List[List[vec3]] = []
    innerGrid: List[List[vec3]] = []
    validGrid: List[List[bool]] = []

    # radio angular del agujero alrededor del polo sur
    # agujero local, no corte global
    openingAngle = math.asin(clamp(openingRadius / radiusBase, 0.0, 0.95))

    for iy in range(phiCount + 1):
        phi = math.pi * iy / phiCount

        outerRow: List[vec3] = []
        innerRow: List[vec3] = []
        validRow: List[bool] = []

        for ix in range(thetaCount + 1):
            theta = 2.0 * math.pi * ix / thetaCount

            reliefField, lightField = sampleField(theta, phi, p)

            reliefValue = reliefField * p.reliefAmount
            thicknessValue = mix(p.maxThickness, p.minThickness, lightField * p.lightAmount)
            thicknessValue = clamp(thicknessValue, p.minThickness, p.maxThickness)

            radiusOuter = radiusBase + reliefValue
            radiusInner = max(radiusOuter - thicknessValue, radiusBase * 0.15)

            outerPoint = sphPoint(radiusOuter, theta, phi)
            innerPoint = sphPoint(radiusInner, theta, phi)

            # recorte local del polo inferior
            # phi cerca de pi => estamos abajo
            keepPoint = phi < (math.pi - openingAngle)

            outerRow.append(outerPoint)
            innerRow.append(innerPoint)
            validRow.append(keepPoint)

        outerGrid.append(outerRow)
        innerGrid.append(innerRow)
        validGrid.append(validRow)

    # cascarón exterior
    for iy in range(phiCount):
        for ix in range(thetaCount):
            if not (
                validGrid[iy][ix]
                and validGrid[iy][ix + 1]
                and validGrid[iy + 1][ix + 1]
                and validGrid[iy + 1][ix]
            ):
                continue

            a = outerGrid[iy][ix]
            b = outerGrid[iy][ix + 1]
            c = outerGrid[iy + 1][ix + 1]
            d = outerGrid[iy + 1][ix]

            triangles.append((a, b, c))
            triangles.append((a, c, d))

    # cascarón interior invertido
    for iy in range(phiCount):
        for ix in range(thetaCount):
            if not (
                validGrid[iy][ix]
                and validGrid[iy][ix + 1]
                and validGrid[iy + 1][ix + 1]
                and validGrid[iy + 1][ix]
            ):
                continue

            a = innerGrid[iy][ix]
            b = innerGrid[iy + 1][ix]
            c = innerGrid[iy + 1][ix + 1]
            d = innerGrid[iy][ix + 1]

            triangles.append((a, b, c))
            triangles.append((a, c, d))

    # encontrar la última fila válida antes del agujero
    rimIndex = None
    for iy in range(phiCount, -1, -1):
        rowOk = any(validGrid[iy][ix] for ix in range(thetaCount))
        if rowOk:
            rimIndex = iy
            break

    if rimIndex is None:
        return triangles

    ringOuter = outerGrid[rimIndex]
    ringInner = innerGrid[rimIndex]

    # cerrar el borde del agujero con una pared entre outer e inner
    for ix in range(thetaCount):
        a = ringOuter[ix]
        b = ringOuter[ix + 1]
        c = ringInner[ix + 1]
        d = ringInner[ix]

        triangles.append((a, b, c))
        triangles.append((a, c, d))

    return triangles


def lampgenPlanetEngine(p: lampgenPlanet) -> None:
    triangles = buildShell(p)
    writeBinaryStl(p.outputPath, triangles)
    print(f"ok: {p.outputPath}")
    print(f"worldType: {p.worldType}")
    print(f"triangles: {len(triangles)}")


def buildArgs() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="lampgenPlanet V1")

    parser.add_argument("--outputPath", type=str, default="lampgenPlanet.stl")
    parser.add_argument("--worldType", type=str, default="naturalWorld", choices=["naturalWorld", "urbanWorld"])

    parser.add_argument("--diameter", type=float, default=160.0)
    parser.add_argument("--minThickness", type=float, default=1.0)
    parser.add_argument("--maxThickness", type=float, default=2.2)

    parser.add_argument("--reliefAmount", type=float, default=0.8)
    parser.add_argument("--lightAmount", type=float, default=1.0)

    parser.add_argument("--thetaSteps", type=int, default=220)
    parser.add_argument("--phiSteps", type=int, default=120)

    parser.add_argument("--openingDiameter", type=float, default=46.0)
    parser.add_argument("--openingFade", type=float, default=10.0)
    parser.add_argument("--poleFade", type=float, default=0.25)
    parser.add_argument("--seed", type=float, default=0.0)

    return parser


def run() -> None:
    parser = buildArgs()
    args = parser.parse_args()

    config = lampgenPlanet(
        outputPath=args.outputPath,
        worldType=args.worldType,
        diameter=args.diameter,
        minThickness=args.minThickness,
        maxThickness=args.maxThickness,
        reliefAmount=args.reliefAmount,
        lightAmount=args.lightAmount,
        thetaSteps=args.thetaSteps,
        phiSteps=args.phiSteps,
        openingDiameter=args.openingDiameter,
        openingFade=args.openingFade,
        poleFade=args.poleFade,
        seed=args.seed,
    )

    lampgenPlanetEngine(config)


run()