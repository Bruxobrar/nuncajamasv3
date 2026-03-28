import argparse
import math
import os
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PIL import Image, ImageFilter


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
    if l <= 1e-12:
        return (0.0, 0.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


def triNormal(a: vec3, b: vec3, c: vec3) -> vec3:
    return vecNorm(vecCross(vecSub(b, a), vecSub(c, a)))


def clamp(v: float, a: float, b: float) -> float:
    return max(a, min(b, v))


def mix(a: float, b: float, t: float) -> float:
    return a * (1.0 - t) + b * t


def smoothstep(a: float, b: float, x: float) -> float:
    if abs(b - a) < 1e-12:
        return 0.0
    t = clamp((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fract(x: float) -> float:
    return x - math.floor(x)


def hash2(a: float, b: float) -> float:
    return fract(math.sin(a * 127.1 + b * 311.7) * 43758.5453123)


def hash3(a: float, b: float, c: float) -> float:
    return fract(math.sin(a * 127.1 + b * 311.7 + c * 191.999) * 43758.5453123)


def valueNoise2(a: float, b: float) -> float:
    ia = math.floor(a)
    ib = math.floor(b)
    fa = a - ia
    fb = b - ib

    v00 = hash2(ia, ib)
    v10 = hash2(ia + 1.0, ib)
    v01 = hash2(ia, ib + 1.0)
    v11 = hash2(ia + 1.0, ib + 1.0)

    ua = fa * fa * (3.0 - 2.0 * fa)
    ub = fb * fb * (3.0 - 2.0 * fb)

    vx0 = mix(v00, v10, ua)
    vx1 = mix(v01, v11, ua)
    return mix(vx0, vx1, ub)


def valueNoise3(a: float, b: float, c: float) -> float:
    ia = math.floor(a)
    ib = math.floor(b)
    ic = math.floor(c)

    fa = a - ia
    fb = b - ib
    fc = c - ic

    u = fa * fa * (3.0 - 2.0 * fa)
    v = fb * fb * (3.0 - 2.0 * fb)
    w = fc * fc * (3.0 - 2.0 * fc)

    c000 = hash3(ia, ib, ic)
    c100 = hash3(ia + 1.0, ib, ic)
    c010 = hash3(ia, ib + 1.0, ic)
    c110 = hash3(ia + 1.0, ib + 1.0, ic)
    c001 = hash3(ia, ib, ic + 1.0)
    c101 = hash3(ia + 1.0, ib, ic + 1.0)
    c011 = hash3(ia, ib + 1.0, ic + 1.0)
    c111 = hash3(ia + 1.0, ib + 1.0, ic + 1.0)

    x00 = mix(c000, c100, u)
    x10 = mix(c010, c110, u)
    x01 = mix(c001, c101, u)
    x11 = mix(c011, c111, u)

    y0 = mix(x00, x10, v)
    y1 = mix(x01, x11, v)

    return mix(y0, y1, w)


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
    if norm <= 1e-12:
        return 0.0
    return total / norm


def fbm3(a: float, b: float, c: float, octaves: int = 5) -> float:
    total = 0.0
    amp = 0.5
    freq = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += valueNoise3(a * freq, b * freq, c * freq) * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    if norm <= 1e-12:
        return 0.0
    return total / norm


def ridgeNoise3(a: float, b: float, c: float, octaves: int = 5) -> float:
    total = 0.0
    amp = 0.5
    freq = 1.0
    norm = 0.0
    for _ in range(octaves):
        n = valueNoise3(a * freq, b * freq, c * freq)
        r = 1.0 - abs(n * 2.0 - 1.0)
        r = r * r
        total += r * amp
        norm += amp
        amp *= 0.5
        freq *= 2.0
    if norm <= 1e-12:
        return 0.0
    return total / norm


def craterShape(dist: float, radius: float, rimWidth: float) -> float:
    if radius <= 1e-9:
        return 0.0
    inner = clamp(1.0 - dist / radius, 0.0, 1.0)
    bowl = -(inner ** 1.6)
    rimStart = radius
    rimEnd = radius + rimWidth
    rimT = smoothstep(rimStart, rimEnd, dist)
    rimBand = 1.0 - rimT
    rim = smoothstep(radius * 0.60, radius, dist) * rimBand * 0.55
    return bowl + rim


def sphPoint(radius: float, theta: float, phi: float) -> vec3:
    sinPhi = math.sin(phi)
    return (
        radius * sinPhi * math.cos(theta),
        radius * sinPhi * math.sin(theta),
        radius * math.cos(phi),
    )


def sphDir(theta: float, phi: float) -> vec3:
    sinPhi = math.sin(phi)
    return (
        sinPhi * math.cos(theta),
        sinPhi * math.sin(theta),
        math.cos(phi),
    )


def angularDistance(thetaA: float, phiA: float, thetaB: float, phiB: float) -> float:
    cosVal = (
        math.sin(phiA) * math.sin(phiB) * math.cos(thetaA - thetaB)
        + math.cos(phiA) * math.cos(phiB)
    )
    cosVal = clamp(cosVal, -1.0, 1.0)
    return math.acos(cosVal)


def writeBinaryStl(path: str, triangles: List[tri3]) -> None:
    header = b"lampgenPlanet V4".ljust(80, b"\0")
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


class lampgenPlanetMap:
    def __init__(self, path: Optional[str] = None, blurRadius: int = 0) -> None:
        self.path = path
        self.width = 0
        self.height = 0
        self.pixels = None

        if path and os.path.isfile(path):
            image = Image.open(path).convert("L")
            if blurRadius > 0:
                image = image.filter(ImageFilter.GaussianBlur(radius=blurRadius))
            self.width, self.height = image.size
            self.pixels = image.load()

    def isReady(self) -> bool:
        return self.pixels is not None and self.width > 1 and self.height > 1

    def sample(self, u: float, v: float) -> float:
        if not self.isReady():
            return 0.0

        u = u % 1.0
        v = clamp(v, 0.0, 1.0)

        x = u * (self.width - 1)
        y = v * (self.height - 1)

        x0 = int(math.floor(x))
        y0 = int(math.floor(y))
        x1 = (x0 + 1) % self.width
        y1 = min(y0 + 1, self.height - 1)

        tx = x - x0
        ty = y - y0

        p00 = self.pixels[x0, y0] / 255.0
        p10 = self.pixels[x1, y0] / 255.0
        p01 = self.pixels[x0, y1] / 255.0
        p11 = self.pixels[x1, y1] / 255.0

        a = mix(p00, p10, tx)
        b = mix(p01, p11, tx)
        return mix(a, b, ty)


@dataclass
class lampgenPlanet:
    outputPath: str = "lampgenPlanet.stl"
    worldType: str = "naturalWorld"

    diameter: float = 160.0
    minThickness: float = 1.0
    maxThickness: float = 2.2

    reliefAmount: float = 2.8
    lightAmount: float = 1.0

    thetaSteps: int = 360
    phiSteps: int = 220

    openingDiameter: float = 46.0
    rimHeight: float = 1.2

    seed: float = 0.0

    reliefPath: Optional[str] = None
    lightPath: Optional[str] = None

    reliefBias: float = 0.0
    reliefContrast: float = 1.0
    lightBias: float = 0.0
    lightContrast: float = 1.0

    polarReliefFade: float = 0.10
    polarLightBoost: float = 0.08
    northPoleSmooth: float = 0.10
    southPoleSmooth: float = 0.08

    reliefBlur: int = 0
    lightBlur: int = 0

    openingBlend: float = 0.06

    terrainForce: float = 1.8
    terrainSharpness: float = 1.6
    cityForce: float = 2.0
    citySharpness: float = 1.8

    craterForce: float = 1.2
    canyonForce: float = 1.1
    districtForce: float = 1.4
    trenchForce: float = 1.1


def remapValue(v: float, bias: float, contrast: float) -> float:
    v = clamp(v + bias, 0.0, 1.0)
    v = (v - 0.5) * contrast + 0.5
    return clamp(v, 0.0, 1.0)


def applyPower(v: float, power: float) -> float:
    v = clamp(v, 0.0, 1.0)
    if power <= 1e-6:
        return v
    return clamp(v ** power, 0.0, 1.0)


def polarBlendFactor(phi: float, northPoleSmooth: float, southPoleSmooth: float) -> float:
    v = phi / math.pi
    northKeep = smoothstep(0.0, northPoleSmooth, v)
    southKeep = smoothstep(0.0, southPoleSmooth, 1.0 - v)
    return northKeep * southKeep


def naturalField(theta: float, phi: float, p: lampgenPlanet) -> Tuple[float, float]:
    x, y, z = sphDir(theta, phi)

    macroA = fbm3(x * 2.2 + 10.0 + p.seed, y * 2.2 + 5.0 + p.seed, z * 2.2 + 3.0 + p.seed, 5)
    macroB = fbm3(x * 4.8 + 20.0 + p.seed, y * 4.6 + 11.0 + p.seed, z * 4.4 + 7.0 + p.seed, 4)
    detailA = fbm3(x * 12.0 + 40.0 + p.seed, y * 12.0 + 21.0 + p.seed, z * 12.0 + 9.0 + p.seed, 4)
    detailB = fbm3(x * 26.0 + 70.0 + p.seed, y * 26.0 + 37.0 + p.seed, z * 26.0 + 13.0 + p.seed, 3)

    ridgeA = ridgeNoise3(x * 5.5 + 14.0 + p.seed, y * 5.2 + 9.0 + p.seed, z * 5.1 + 6.0 + p.seed, 5)
    ridgeB = ridgeNoise3(x * 12.0 + 50.0 + p.seed, y * 11.0 + 17.0 + p.seed, z * 11.5 + 4.0 + p.seed, 4)

    landRaw = macroA * 0.45 + macroB * 0.25 + detailA * 0.20 + detailB * 0.10
    landMask = smoothstep(0.42, 0.60, landRaw)
    seaMask = 1.0 - landMask

    mountainMask = smoothstep(0.50, 0.82, ridgeA * 0.65 + ridgeB * 0.35) * landMask
    plateauMask = smoothstep(0.58, 0.80, macroB) * landMask
    valleyMask = smoothstep(0.60, 0.86, 1.0 - ridgeA) * landMask

    canyonNoise = ridgeNoise3(x * 9.0 + 90.0 + p.seed, y * 9.0 + 34.0 + p.seed, z * 9.0 + 22.0 + p.seed, 4)
    canyonMask = smoothstep(0.68, 0.90, canyonNoise) * landMask
    craterMask = smoothstep(0.64, 0.84, detailB) * landMask * p.craterForce * 0.30

    craterField = 0.0
    craterField += craterShape(angularDistance(theta, phi, 0.70, 1.15), 0.19, 0.05) * 0.65
    craterField += craterShape(angularDistance(theta, phi, 3.90, 1.95), 0.16, 0.04) * 0.55
    craterField += craterShape(angularDistance(theta, phi, 2.20, 0.95), 0.13, 0.04) * 0.45
    craterField += craterShape(angularDistance(theta, phi, 5.15, 2.35), 0.11, 0.03) * 0.38
    craterField *= landMask * p.craterForce

    oceanFloor = smoothstep(0.50, 0.92, detailA * 0.50 + detailB * 0.50) * seaMask

    relief = 0.0
    relief += landMask * 0.35
    relief += plateauMask * 0.18
    relief += mountainMask * 0.70 * p.terrainForce
    relief += canyonMask * 0.28 * p.canyonForce
    relief += craterMask * 0.18
    relief += craterField * 0.50
    relief -= valleyMask * 0.24 * p.canyonForce
    relief -= oceanFloor * 0.26
    relief -= seaMask * 0.14

    relief = (relief + 0.22) * p.terrainForce
    relief = clamp(relief, 0.0, 1.0)
    relief = applyPower(relief, 1.0 / max(0.15, p.terrainSharpness))

    light = 0.0
    light += seaMask * 0.82
    light += landMask * 0.28
    light -= mountainMask * 0.22
    light -= plateauMask * 0.08
    light += valleyMask * 0.08
    light += canyonMask * 0.06
    light += (0.5 - craterField) * 0.05
    light += (1.0 - abs(z)) * p.polarLightBoost

    light = clamp(light, 0.0, 1.0)
    return relief, light


def urbanField(theta: float, phi: float, p: lampgenPlanet) -> Tuple[float, float]:
    x, y, z = sphDir(theta, phi)

    majorA = ridgeNoise3(x * 4.5 + 10.0 + p.seed, y * 4.5 + 20.0 + p.seed, z * 4.5 + 4.0 + p.seed, 5)
    majorB = ridgeNoise3(x * 8.0 + 30.0 + p.seed, y * 8.0 + 12.0 + p.seed, z * 8.0 + 8.0 + p.seed, 4)
    fineA = ridgeNoise3(x * 18.0 + 50.0 + p.seed, y * 18.0 + 17.0 + p.seed, z * 18.0 + 9.0 + p.seed, 4)
    fineB = ridgeNoise3(x * 34.0 + 80.0 + p.seed, y * 34.0 + 22.0 + p.seed, z * 34.0 + 11.0 + p.seed, 3)

    districtNoise = fbm3(x * 4.2 + 16.0 + p.seed, y * 4.0 + 8.0 + p.seed, z * 4.1 + 6.0 + p.seed, 5)
    nodeNoise = fbm3(x * 18.0 + 120.0 + p.seed, y * 18.0 + 60.0 + p.seed, z * 18.0 + 15.0 + p.seed, 4)

    roadMain = smoothstep(0.58, 0.84, majorA * 0.55 + majorB * 0.45)
    roadMid = smoothstep(0.62, 0.88, fineA)
    roadFine = smoothstep(0.70, 0.92, fineB)
    districtMask = smoothstep(0.48, 0.72, districtNoise)
    nodeMask = smoothstep(0.56, 0.82, nodeNoise)

    equatorBias = math.pow(1.0 - abs(z), 1.2)

    trenchNoise = ridgeNoise3(x * 2.5 + 200.0 + p.seed, y * 2.5 + 35.0 + p.seed, z * 2.5 + 17.0 + p.seed, 4)
    trenchMask = smoothstep(0.70, 0.90, trenchNoise)

    scar = craterShape(angularDistance(theta, phi, 4.10, 1.57), 0.42, 0.05)
    scarMask = clamp(-scar, 0.0, 1.0)

    relief = 0.0
    relief += districtMask * 0.16 * p.districtForce
    relief += roadMain * 0.38 * p.cityForce
    relief += roadMid * 0.24 * p.cityForce
    relief += roadFine * 0.14 * p.cityForce
    relief += nodeMask * 0.22 * p.cityForce
    relief += equatorBias * 0.08
    relief -= trenchMask * 0.35 * p.trenchForce
    relief -= scarMask * 0.55 * p.trenchForce

    relief = (relief + 0.18) * p.cityForce
    relief = clamp(relief, 0.0, 1.0)
    relief = applyPower(relief, 1.0 / max(0.15, p.citySharpness))

    light = 0.0
    light += roadMain * 0.72
    light += roadMid * 0.42
    light += roadFine * 0.22
    light += nodeMask * 0.34
    light += equatorBias * 0.12
    light += districtMask * 0.10
    light -= trenchMask * 0.16
    light -= scarMask * 0.28

    light = clamp(light, 0.0, 1.0)
    return relief, light


def sampleField(
    theta: float,
    phi: float,
    p: lampgenPlanet,
    reliefMap: lampgenPlanetMap,
    lightMap: lampgenPlanetMap,
) -> Tuple[float, float]:
    u = theta / (2.0 * math.pi)
    v = phi / math.pi

    if p.worldType == "urbanWorld":
        baseRelief, baseLight = urbanField(theta, phi, p)
    else:
        baseRelief, baseLight = naturalField(theta, phi, p)

    if reliefMap.isReady():
        mapRelief = reliefMap.sample(u, v)
        mapRelief = remapValue(mapRelief, p.reliefBias, p.reliefContrast)
        relief = mapRelief
    else:
        relief = baseRelief

    if lightMap.isReady():
        mapLight = lightMap.sample(u, v)
        mapLight = remapValue(mapLight, p.lightBias, p.lightContrast)
        light = mapLight
    else:
        light = baseLight

    poleKeep = polarBlendFactor(phi, p.northPoleSmooth, p.southPoleSmooth)
    relief = mix(0.0, relief, poleKeep)

    return clamp(relief, 0.0, 1.0), clamp(light, 0.0, 1.0)


def buildShell(p: lampgenPlanet) -> List[tri3]:
    triangles: List[tri3] = []

    radiusBase = p.diameter * 0.5
    openingRadius = p.openingDiameter * 0.5

    thetaCount = max(64, p.thetaSteps)
    phiCount = max(48, p.phiSteps)

    reliefMap = lampgenPlanetMap(p.reliefPath, p.reliefBlur)
    lightMap = lampgenPlanetMap(p.lightPath, p.lightBlur)

    if openingRadius >= radiusBase * 0.95:
        raise ValueError("openingDiameter demasiado grande para el diámetro total")

    openingAngle = math.asin(clamp(openingRadius / radiusBase, 0.0, 0.95))
    rimPhi = math.pi - openingAngle

    outerGrid: List[List[vec3]] = []
    innerGrid: List[List[vec3]] = []
    keepGrid: List[List[bool]] = []

    for iy in range(phiCount + 1):
        phi = math.pi * iy / phiCount

        outerRow: List[vec3] = []
        innerRow: List[vec3] = []
        keepRow: List[bool] = []

        for ix in range(thetaCount):
            theta = 2.0 * math.pi * ix / thetaCount

            reliefField, lightField = sampleField(theta, phi, p, reliefMap, lightMap)

            openingBlendStart = rimPhi - p.openingBlend
            openingFade = smoothstep(openingBlendStart, rimPhi, phi)
            reliefField = mix(reliefField, 0.0, openingFade)

            reliefValue = reliefField * p.reliefAmount

            lightField = clamp(lightField, 0.0, 1.0)
            thicknessValue = mix(
                p.maxThickness,
                p.minThickness,
                clamp(lightField * p.lightAmount, 0.0, 1.0),
            )
            thicknessValue = clamp(thicknessValue, p.minThickness, p.maxThickness)

            radiusOuter = radiusBase + reliefValue
            radiusInner = max(radiusOuter - thicknessValue, radiusBase * 0.15)

            outerPoint = sphPoint(radiusOuter, theta, phi)
            innerPoint = sphPoint(radiusInner, theta, phi)

            keepPoint = phi <= rimPhi + 1e-9

            outerRow.append(outerPoint)
            innerRow.append(innerPoint)
            keepRow.append(keepPoint)

        outerGrid.append(outerRow)
        innerGrid.append(innerRow)
        keepGrid.append(keepRow)

    for iy in range(phiCount):
        for ix in range(thetaCount):
            ix1 = (ix + 1) % thetaCount

            if keepGrid[iy][ix] and keepGrid[iy][ix1] and keepGrid[iy + 1][ix1] and keepGrid[iy + 1][ix]:
                a = outerGrid[iy][ix]
                b = outerGrid[iy][ix1]
                c = outerGrid[iy + 1][ix1]
                d = outerGrid[iy + 1][ix]

                triangles.append((a, b, c))
                triangles.append((a, c, d))

    for iy in range(phiCount):
        for ix in range(thetaCount):
            ix1 = (ix + 1) % thetaCount

            if keepGrid[iy][ix] and keepGrid[iy][ix1] and keepGrid[iy + 1][ix1] and keepGrid[iy + 1][ix]:
                a = innerGrid[iy][ix]
                b = innerGrid[iy + 1][ix]
                c = innerGrid[iy + 1][ix1]
                d = innerGrid[iy][ix1]

                triangles.append((a, b, c))
                triangles.append((a, c, d))

    rimIndex = None
    for iy in range(phiCount, -1, -1):
        rowValid = all(keepGrid[iy][ix] for ix in range(thetaCount))
        if rowValid:
            rimIndex = iy
            break

    if rimIndex is None:
        return triangles

    ringOuter = outerGrid[rimIndex]
    ringInner = innerGrid[rimIndex]

    if p.rimHeight > 0.0:
        rimOuter2: List[vec3] = []
        rimInner2: List[vec3] = []

        for ix in range(thetaCount):
            po = ringOuter[ix]
            pi = ringInner[ix]

            no = vecNorm(po)
            ni = vecNorm(pi)

            rimOuter2.append(
                (po[0] - no[0] * p.rimHeight, po[1] - no[1] * p.rimHeight, po[2] - no[2] * p.rimHeight)
            )
            rimInner2.append(
                (pi[0] - ni[0] * p.rimHeight, pi[1] - ni[1] * p.rimHeight, pi[2] - ni[2] * p.rimHeight)
            )

        for ix in range(thetaCount):
            ix1 = (ix + 1) % thetaCount

            a = ringOuter[ix]
            b = ringOuter[ix1]
            c = rimOuter2[ix1]
            d = rimOuter2[ix]

            triangles.append((a, b, c))
            triangles.append((a, c, d))

            a = rimInner2[ix]
            b = rimInner2[ix1]
            c = ringInner[ix1]
            d = ringInner[ix]

            triangles.append((a, b, c))
            triangles.append((a, c, d))

            a = rimOuter2[ix]
            b = rimOuter2[ix1]
            c = rimInner2[ix1]
            d = rimInner2[ix]

            triangles.append((a, b, c))
            triangles.append((a, c, d))
    else:
        for ix in range(thetaCount):
            ix1 = (ix + 1) % thetaCount

            a = ringOuter[ix]
            b = ringOuter[ix1]
            c = ringInner[ix1]
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
    print(f"reliefPath: {p.reliefPath}")
    print(f"lightPath: {p.lightPath}")


def buildArgs() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="lampgenPlanet V4")

    parser.add_argument("--outputPath", type=str, default="lampgenPlanet.stl")
    parser.add_argument("--worldType", type=str, default="naturalWorld", choices=["naturalWorld", "urbanWorld"])

    parser.add_argument("--diameter", type=float, default=160.0)
    parser.add_argument("--minThickness", type=float, default=1.0)
    parser.add_argument("--maxThickness", type=float, default=2.2)

    parser.add_argument("--reliefAmount", type=float, default=2.8)
    parser.add_argument("--lightAmount", type=float, default=1.0)

    parser.add_argument("--thetaSteps", type=int, default=360)
    parser.add_argument("--phiSteps", type=int, default=220)

    parser.add_argument("--openingDiameter", type=float, default=46.0)
    parser.add_argument("--rimHeight", type=float, default=1.2)

    parser.add_argument("--seed", type=float, default=0.0)

    parser.add_argument("--reliefPath", type=str, default=None)
    parser.add_argument("--lightPath", type=str, default=None)

    parser.add_argument("--reliefBias", type=float, default=0.0)
    parser.add_argument("--reliefContrast", type=float, default=1.0)
    parser.add_argument("--lightBias", type=float, default=0.0)
    parser.add_argument("--lightContrast", type=float, default=1.0)

    parser.add_argument("--polarReliefFade", type=float, default=0.10)
    parser.add_argument("--polarLightBoost", type=float, default=0.08)
    parser.add_argument("--northPoleSmooth", type=float, default=0.10)
    parser.add_argument("--southPoleSmooth", type=float, default=0.08)

    parser.add_argument("--reliefBlur", type=int, default=0)
    parser.add_argument("--lightBlur", type=int, default=0)

    parser.add_argument("--openingBlend", type=float, default=0.06)

    parser.add_argument("--terrainForce", type=float, default=1.8)
    parser.add_argument("--terrainSharpness", type=float, default=1.6)
    parser.add_argument("--cityForce", type=float, default=2.0)
    parser.add_argument("--citySharpness", type=float, default=1.8)

    parser.add_argument("--craterForce", type=float, default=1.2)
    parser.add_argument("--canyonForce", type=float, default=1.1)
    parser.add_argument("--districtForce", type=float, default=1.4)
    parser.add_argument("--trenchForce", type=float, default=1.1)

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
        rimHeight=args.rimHeight,
        seed=args.seed,
        reliefPath=args.reliefPath,
        lightPath=args.lightPath,
        reliefBias=args.reliefBias,
        reliefContrast=args.reliefContrast,
        lightBias=args.lightBias,
        lightContrast=args.lightContrast,
        polarReliefFade=args.polarReliefFade,
        polarLightBoost=args.polarLightBoost,
        northPoleSmooth=args.northPoleSmooth,
        southPoleSmooth=args.southPoleSmooth,
        reliefBlur=args.reliefBlur,
        lightBlur=args.lightBlur,
        openingBlend=args.openingBlend,
        terrainForce=args.terrainForce,
        terrainSharpness=args.terrainSharpness,
        cityForce=args.cityForce,
        citySharpness=args.citySharpness,
        craterForce=args.craterForce,
        canyonForce=args.canyonForce,
        districtForce=args.districtForce,
        trenchForce=args.trenchForce,
    )

    lampgenPlanetEngine(config)


run()