"""Render eggbeater performance plots as a body-only HTML fragment (inline SVG).

Driven by DesignResult objects; overlays multiple designs per chart.
"""

import html
import json
import math
from functools import cache
from importlib.resources import files

from .design import (
    AR_TARGET_DB,
    NEC_SENSE_TO_HAND,
    VSWR_LIMIT,
    DesignResult,
    _axial_ratio_db,
    _operating_point,
    analyze,
    bandwidth_within,
    frequency_sweep,
    post_match_vswr,
    tuned_geometry,
)
from .geometry import LOOP_B_TAG_BASE, RADIAL_TAG_BASE
from .nec import RadiationGrid
from .report import cut_sheet_build
from .spec import spec_to_dict

# Data trace colors, cycled per design (teal, amber, violet, green, ...).
TRACE_COLORS = ("#0E7C86", "#C8881C", "#6D4AA7", "#357960", "#B5532A")
LIMIT_COLOR = "#B23A48"
GRID_COLOR = "#DCE3E1"
AXIS_COLOR = "#9FB0AC"

# Fine principal-plane (phi = 0) grid for elevation cuts, theta 0..90 deg.
FINE_GRID = RadiationGrid(ntheta=46, nphi=1, theta0=0.0, phi0=0.0, dtheta=2.0, dphi=0.0)
# Full upper hemisphere for the az-el maps: theta 0..90 by 10, phi 0..360 by 15.
HEMI_GRID = RadiationGrid(
    ntheta=10, nphi=25, theta0=0.0, phi0=0.0, dtheta=10.0, dphi=15.0
)
HEMI_THETAS = tuple(range(0, 100, 10))
HEMI_PHIS = tuple(range(0, 360, 15))
SWEEP_SPAN_FRACTION = 0.10
SWEEP_POINTS = 61
# Display clamps so near-linear horizon spikes stay on-axis.
AR_CLAMP_DB = 10.0
VSWR_CLAMP = 3.0
GAIN_FLOOR_DB = -50.0
# Az-el map ranges: gain spans this many dB below the peak; AR clamps at this dB.
GAIN_MAP_RANGE_DB = 18.0
AR_MAP_MAX_DB = 6.0

# The 3-D wireframe viewer (orbit/zoom) lives in viewer.js; its palette (loop A,
# loop B, radial) matches the indices set by _wire_color_index, feed = LIMIT_COLOR.

# Colormap stops (position 0..1 -> RGB) for the gain and axial-ratio maps.
GAIN_CMAP = ((0.0, (16, 43, 64)), (0.55, (33, 120, 110)), (1.0, (242, 201, 76)))
AR_CMAP = ((0.0, (14, 124, 134)), (0.5, (200, 136, 28)), (1.0, (178, 58, 72)))

# SVG chart geometry.
_W, _H = 460, 300
_ML, _MR, _MT, _MB = 56, 18, 16, 44


def _label(result: DesignResult) -> str:
    return result.spec.label or f"{result.spec.freq_mhz:g} MHz"


def _elevation_cut(result: DesignResult):
    """Axial ratio and gain versus elevation on the phi=0 plane."""
    spec = result.spec
    factor_a, factor_b, phase_b = _operating_point(
        result.base_factor, result.delta, spec.phasing, flip=False
    )
    nec, _ = analyze(spec, factor_a, factor_b, phase_b, grid=FINE_GRID)
    ar, gain = [], []
    for point in nec.pattern:
        elevation = 90.0 - point.theta_deg
        ar.append((elevation, min(_axial_ratio_db(point.axial_ratio), AR_CLAMP_DB)))
        if point.total_gain_db > GAIN_FLOOR_DB:
            gain.append((elevation, point.total_gain_db))
    ar.sort()
    gain.sort()
    return ar, gain


def _collect(result: DesignResult) -> dict:
    spec = result.spec
    f0 = spec.freq_mhz
    sweep = frequency_sweep(result, SWEEP_SPAN_FRACTION, SWEEP_POINTS)
    vswr_pairs = [(p.freq_mhz, p.vswr) for p in sweep]
    ar_pairs = [(p.freq_mhz, p.ar_db) for p in sweep]
    ar_elev, gain_elev = _elevation_cut(result)
    return {
        "label": _label(result),
        "f0": f0,
        "z": result.z_in,
        "sense": (NEC_SENSE_TO_HAND.get(result.sense) or result.sense).upper(),
        "vswr_post": post_match_vswr(result.z_in),
        "ar_cone": result.ar_boresight_db,
        "cov_gain": result.coverage_gain_db,
        "vswr_band": bandwidth_within(vswr_pairs, VSWR_LIMIT),
        "ar_band": bandwidth_within(ar_pairs, AR_TARGET_DB),
        "vswr_freq": [
            (100.0 * (f - f0) / f0, min(v, VSWR_CLAMP)) for f, v in vswr_pairs
        ],
        "ar_freq": [(100.0 * (f - f0) / f0, min(a, AR_CLAMP_DB)) for f, a in ar_pairs],
        "ar_elev": ar_elev,
        "gain_elev": gain_elev,
    }


def _sx(x, xmin, xmax):
    return _ML + (x - xmin) / (xmax - xmin) * (_W - _ML - _MR)


def _sy(y, ymin, ymax):
    return (_H - _MB) - (y - ymin) / (ymax - ymin) * (_H - _MT - _MB)


def _polyline(pts, xmin, xmax, ymin, ymax, color):
    coords = " ".join(
        f"{_sx(x, xmin, xmax):.1f},{_sy(y, ymin, ymax):.1f}" for x, y in pts
    )
    return (
        f'<polyline fill="none" stroke="{color}" stroke-width="2.4" '
        f'stroke-linejoin="round" stroke-linecap="round" points="{coords}" />'
    )


def _chart(
    series,
    xmin,
    xmax,
    xticks,
    ymin,
    ymax,
    yticks,
    xlabel,
    ylabel,
    fmt_y="{:g}",
    limit=None,
    limit_label="",
):
    parts = [
        f'<svg viewBox="0 0 {_W} {_H}" role="img" preserveAspectRatio="xMidYMid meet">'
    ]
    for ty in yticks:
        y = _sy(ty, ymin, ymax)
        parts.append(
            f'<line x1="{_ML}" y1="{y:.1f}" x2="{_W - _MR}" y2="{y:.1f}" '
            f'stroke="{GRID_COLOR}" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{_ML - 8}" y="{y + 3.5:.1f}" text-anchor="end" '
            f'class="tick">{fmt_y.format(ty)}</text>'
        )
    for tx in xticks:
        x = _sx(tx, xmin, xmax)
        parts.append(
            f'<line x1="{x:.1f}" y1="{_MT}" x2="{x:.1f}" y2="{_H - _MB}" '
            f'stroke="{GRID_COLOR}" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{_H - _MB + 16}" text-anchor="middle" '
            f'class="tick">{tx:g}</text>'
        )
    if limit is not None and ymin <= limit <= ymax:
        y = _sy(limit, ymin, ymax)
        parts.append(
            f'<line x1="{_ML}" y1="{y:.1f}" x2="{_W - _MR}" y2="{y:.1f}" '
            f'stroke="{LIMIT_COLOR}" stroke-width="1.4" stroke-dasharray="5 4" />'
        )
        parts.append(
            f'<text x="{_W - _MR - 4}" y="{y - 5:.1f}" text-anchor="end" '
            f'class="limit">{html.escape(limit_label)}</text>'
        )
    parts.append(
        f'<rect x="{_ML}" y="{_MT}" width="{_W - _ML - _MR}" '
        f'height="{_H - _MT - _MB}" fill="none" stroke="{AXIS_COLOR}" '
        f'stroke-width="1.2" />'
    )
    for color, _, pts in series:
        if pts:
            parts.append(_polyline(pts, xmin, xmax, ymin, ymax, color))
    parts.append(
        f'<text x="{_ML + (_W - _ML - _MR) / 2:.1f}" y="{_H - 6}" '
        f'text-anchor="middle" class="axis">{html.escape(xlabel)}</text>'
    )
    cy = _MT + (_H - _MT - _MB) / 2
    parts.append(
        f'<text x="14" y="{cy:.1f}" text-anchor="middle" class="axis" '
        f'transform="rotate(-90 14 {cy:.1f})">{html.escape(ylabel)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _lerp_color(cmap, t):
    """Interpolate an RGB tuple from colormap stops at position t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    for (p0, c0), (p1, c1) in zip(cmap, cmap[1:], strict=False):
        if t <= p1:
            f = (t - p0) / (p1 - p0) if p1 > p0 else 0.0
            return tuple(round(c0[i] + (c1[i] - c0[i]) * f) for i in range(3))
    return cmap[-1][1]


def _hemisphere(result: DesignResult):
    """Gain (dBi) and axial ratio (dB) over the upper hemisphere, by (theta, phi).

    One nec2c run on a theta x phi grid; phi is taken modulo 360 so the 360 deg
    sample folds onto 0.
    """
    spec = result.spec
    factor_a, factor_b, phase_b = _operating_point(
        result.base_factor, result.delta, spec.phasing, flip=False
    )
    nec, _ = analyze(spec, factor_a, factor_b, phase_b, grid=HEMI_GRID)
    gain, ar = {}, {}
    for point in nec.pattern:
        key = (round(point.theta_deg), round(point.phi_deg) % 360)
        gain[key] = point.total_gain_db
        ar[key] = min(_axial_ratio_db(point.axial_ratio), AR_MAP_MAX_DB)
    return gain, ar


def _polar_xy(cx, cy, radius, theta, phi):
    """Project (theta from zenith, phi azimuth) to screen: zenith at the centre,
    phi = 0 at the top increasing clockwise."""
    r = radius * theta / 90.0
    a = math.radians(phi)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def _sector_path(cx, cy, radius, t0, t1, p0, p1):
    xo0, yo0 = _polar_xy(cx, cy, radius, t1, p0)
    xo1, yo1 = _polar_xy(cx, cy, radius, t1, p1)
    r1 = radius * t1 / 90.0
    if t0 <= 0.0:  # innermost ring is a pie slice from the centre
        return (
            f"M{cx:.1f},{cy:.1f} L{xo0:.1f},{yo0:.1f} "
            f"A{r1:.1f},{r1:.1f} 0 0 1 {xo1:.1f},{yo1:.1f} Z"
        )
    xi0, yi0 = _polar_xy(cx, cy, radius, t0, p0)
    xi1, yi1 = _polar_xy(cx, cy, radius, t0, p1)
    r0 = radius * t0 / 90.0
    return (
        f"M{xi0:.1f},{yi0:.1f} L{xo0:.1f},{yo0:.1f} "
        f"A{r1:.1f},{r1:.1f} 0 0 1 {xo1:.1f},{yo1:.1f} "
        f"L{xi1:.1f},{yi1:.1f} A{r0:.1f},{r0:.1f} 0 0 0 {xi0:.1f},{yi0:.1f} Z"
    )


def _polar_heatmap(values, vmin, vmax, cmap, bar_label):
    """Polar az-el heatmap: zenith at the centre, horizon at the rim."""
    cx, cy, radius = 150.0, 150.0, 120.0
    parts = [
        '<svg viewBox="0 0 360 300" role="img" preserveAspectRatio="xMidYMid meet">'
    ]
    span = vmax - vmin or 1.0
    for i in range(len(HEMI_THETAS) - 1):
        t0, t1 = HEMI_THETAS[i], HEMI_THETAS[i + 1]
        for p0 in HEMI_PHIS:
            p1 = p0 + 15
            corners = [values.get((t, p % 360)) for t in (t0, t1) for p in (p0, p1)]
            corners = [c for c in corners if c is not None]
            if not corners:
                continue
            color = _hex(_lerp_color(cmap, (sum(corners) / len(corners) - vmin) / span))
            parts.append(
                f'<path d="{_sector_path(cx, cy, radius, t0, t1, p0, p1)}" fill="{color}" />'
            )
    for theta in (30, 60, 90):
        r = radius * theta / 90.0
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" '
            f'stroke="{AXIS_COLOR}" stroke-width="0.8" opacity="0.55" />'
        )
        parts.append(
            f'<text x="{cx + 3}" y="{cy - r + 11:.1f}" class="tick">{theta}&#176;</text>'
        )
    for az in (0, 90, 180, 270):
        lx, ly = _polar_xy(cx, cy, radius + 14, 90, az)
        parts.append(
            f'<text x="{lx:.1f}" y="{ly + 3:.1f}" text-anchor="middle" class="tick">{az}&#176;</text>'
        )
    parts.append(_colorbar(vmin, vmax, cmap, bar_label))
    parts.append("</svg>")
    return "".join(parts)


def _colorbar(vmin, vmax, cmap, label):
    bx, by, bw, bh, n = 318.0, 50.0, 12.0, 190.0, 32
    parts = []
    for k in range(n):
        t = k / (n - 1)
        y = by + bh * (1.0 - t) - bh / n
        parts.append(
            f'<rect x="{bx}" y="{y:.1f}" width="{bw}" height="{bh / n + 1.0:.1f}" '
            f'fill="{_hex(_lerp_color(cmap, t))}" />'
        )
    parts.append(
        f'<text x="{bx + bw + 4}" y="{by + 4:.1f}" class="tick">{vmax:.0f}</text>'
    )
    parts.append(
        f'<text x="{bx + bw + 4}" y="{by + bh:.1f}" class="tick">{vmin:.0f}</text>'
    )
    parts.append(
        f'<text x="{bx + bw / 2:.1f}" y="{by - 8:.1f}" text-anchor="middle" '
        f'class="tick">{html.escape(label)}</text>'
    )
    return "".join(parts)


@cache
def _viewer_script() -> str:
    """The orbit-viewer JS (viewer.js) wrapped in a script tag, inlined once so
    the page stays self-contained."""
    js = files("beater").joinpath("viewer.js").read_text(encoding="utf-8")
    return f"<script>\n{js}</script>"


def _wire_color_index(tag):
    """0 = loop A, 1 = loop B, 2 = reflector radial (indexes the viewer palette)."""
    if tag < LOOP_B_TAG_BASE:
        return 0
    if tag < RADIAL_TAG_BASE:
        return 1
    return 2


def _wireframe(result: DesignResult, index: int):
    """Interactive 3-D wire model: a canvas plus its geometry as inline JSON.

    The tuned wires (each [x1,y1,z1,x2,y2,z2,color_index], metres) and feed points
    are emitted as data; the shared viewer script (see _VIEWER_SCRIPT) orbits and
    zooms them on the client. No deck parsing and no 3-D library.
    """
    wires, feeds = tuned_geometry(result)
    payload = json.dumps(
        {
            "wires": [
                [
                    round(w.x1, 5),
                    round(w.y1, 5),
                    round(w.z1, 5),
                    round(w.x2, 5),
                    round(w.y2, 5),
                    round(w.z2, 5),
                    _wire_color_index(w.tag),
                ]
                for w in wires
            ],
            "feeds": [[round(f[0], 5), round(f[1], 5), round(f[2], 5)] for f in feeds],
        }
    )
    cid = f"geom{index}"
    return (
        f'<canvas class="viewer" id="{cid}" width="300" height="300" '
        'aria-label="Interactive 3-D wire model; drag to orbit, scroll to zoom">'
        f'</canvas><script type="application/json" id="{cid}-data">{payload}</script>'
    )


def _spatial(results: list[DesignResult]) -> str:
    """Per-design interactive geometry and gain/axial-ratio az-el maps."""
    blocks = []
    for index, result in enumerate(results):
        gain, ar = _hemisphere(result)
        gmax = math.ceil(max(gain.values()))
        gain_svg = _polar_heatmap(
            gain, gmax - GAIN_MAP_RANGE_DB, gmax, GAIN_CMAP, "dBi"
        )
        ar_svg = _polar_heatmap(ar, 0.0, AR_MAP_MAX_DB, AR_CMAP, "dB")
        wire_svg = _wireframe(result, index)
        blocks.append(
            f'<section class="detail"><h2>{html.escape(_label(result))} '
            "&mdash; geometry and az-el maps</h2>"
            '<div class="trio">'
            + _figure(
                "Geometry (drag to orbit)",
                "Crossed loops (teal / violet) and reflector radials (grey); "
                "red marks each loop feed. Drag to orbit, scroll to zoom.",
                wire_svg,
            )
            + _figure(
                "Gain over the sky",
                "Total gain by azimuth and elevation; centre is overhead, rim "
                "the horizon. Rings mark zenith angle.",
                gain_svg,
            )
            + _figure(
                "Axial ratio over the sky",
                "CP quality by azimuth and elevation; teal is circular, red "
                "linear. Amber is the 3 dB edge of usable coverage.",
                ar_svg,
            )
            + "</div></section>"
        )
    return "".join(blocks)


def _figure(title, note, svg):
    return (
        f'<figure class="card"><figcaption>{html.escape(title)}</figcaption>'
        f'{svg}<p class="note">{html.escape(note)}</p></figure>'
    )


def _band_text(band):
    return "not met" if band is None else f"{band[0]:.1f}&ndash;{band[1]:.1f} MHz"


def _details(results: list[DesignResult]) -> str:
    """Per-design input spec (JSON) and physical cut sheet, as <pre> blocks."""
    blocks = []
    for result in results:
        spec_json = html.escape(json.dumps(spec_to_dict(result.spec), indent=2))
        sheet = html.escape(cut_sheet_build(result))
        blocks.append(
            f'<section class="detail"><h2>{html.escape(_label(result))}</h2>'
            '<div class="cols">'
            f"<div><h3>Input spec</h3><pre>{spec_json}</pre></div>"
            f"<div><h3>Cut list</h3><pre>{sheet}</pre></div>"
            "</div></section>"
        )
    return "".join(blocks)


def render_artifact(results: list[DesignResult]) -> str:
    """Build the body-only HTML for one or more designs."""
    data = [_collect(r) for r in results]
    colors = {
        d["label"]: TRACE_COLORS[i % len(TRACE_COLORS)] for i, d in enumerate(data)
    }

    def series(key):
        return [(colors[d["label"]], d["label"], d[key]) for d in data]

    gains = [g for d in data for _, g in d["gain_elev"]] or [0.0]
    gmin = 2 * (int(min(gains)) // 2) - 2
    gmax = 2 * (int(max(gains)) // 2) + 2

    charts = "".join(
        [
            _figure(
                "Matched VSWR vs frequency",
                "Reflected power across the band; stays under 2:1 over a wide span.",
                _chart(
                    series("vswr_freq"),
                    -10,
                    10,
                    [-10, -5, 0, 5, 10],
                    1.0,
                    3.0,
                    [1.0, 1.5, 2.0, 2.5, 3.0],
                    "frequency offset (%)",
                    "VSWR",
                    fmt_y="{:.1f}",
                    limit=2.0,
                    limit_label="2:1",
                ),
            ),
            _figure(
                "Axial ratio vs frequency",
                "CP quality vs frequency; the 3 dB crossings bound usable coverage.",
                _chart(
                    series("ar_freq"),
                    -10,
                    10,
                    [-10, -5, 0, 5, 10],
                    0.0,
                    10.0,
                    [0, 2, 4, 6, 8, 10],
                    "frequency offset (%)",
                    "axial ratio (dB)",
                    limit=3.0,
                    limit_label="3 dB",
                ),
            ),
            _figure(
                "Axial ratio vs elevation",
                "CP quality from horizon to zenith; best overhead, linear near the horizon.",
                _chart(
                    series("ar_elev"),
                    0,
                    90,
                    [0, 30, 60, 90],
                    0.0,
                    10.0,
                    [0, 2, 4, 6, 8, 10],
                    "elevation (deg)",
                    "axial ratio (dB)",
                    limit=3.0,
                    limit_label="3 dB",
                ),
            ),
            _figure(
                "Gain vs elevation",
                "Coverage vs elevation angle; favors high-angle (overhead) passes.",
                _chart(
                    series("gain_elev"),
                    0,
                    90,
                    [0, 30, 60, 90],
                    gmin,
                    gmax,
                    list(range(gmin, gmax + 1, 2)),
                    "elevation (deg)",
                    "gain (dBi)",
                ),
            ),
        ]
    )

    legend = "".join(
        f'<span><span class="key" style="background:{colors[d["label"]]}"></span>'
        f"{html.escape(d['label'])} ({d['f0']:g} MHz)</span>"
        for d in data
    )
    legend += (
        f'<span><span class="key" style="background:{LIMIT_COLOR}"></span>'
        "design limit</span>"
    )

    rows = "".join(
        f'<tr><td><span class="chip" style="background:{colors[d["label"]]}"></span>'
        f"{html.escape(d['label'])}</td>"
        f"<td>{d['f0']:.1f}</td>"
        f"<td>{d['z'].real:.0f} {d['z'].imag:+.0f}j</td>"
        f"<td>{d['sense']}</td>"
        f"<td>{d['vswr_post']:.2f}</td>"
        f"<td>{d['ar_cone']:.2f}</td>"
        f"<td>{d['cov_gain']:.1f}</td>"
        f"<td>{_band_text(d['vswr_band'])}</td>"
        f"<td>{_band_text(d['ar_band'])}</td></tr>"
        for d in data
    )

    return _TEMPLATE.replace("{LIMIT}", LIMIT_COLOR).format(
        rows=rows,
        legend=legend,
        charts=charts,
        spatial=_spatial(results),
        details=_details(results),
        viewer=_viewer_script(),
    )


_TEMPLATE = """<title>Eggbeater Performance</title>
<meta name="description" content="nec2c-modeled eggbeater antenna performance: VSWR, axial ratio, and elevation coverage.">
<style>
  :root {{
    --ground:#F3F5F4; --ink:#16211F; --muted:#5A6B67; --line:#C9D3D0;
    --panel:#FFFFFF; --teal:#0E7C86;
    --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,"SF Mono","Cascadia Code",Menlo,Consolas,monospace;
  }}
  body {{ margin:0; background:var(--ground); color:var(--ink);
    font-family:var(--sans); line-height:1.5; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:980px; margin:0 auto; padding:40px 24px 64px; }}
  .eyebrow {{ font-family:var(--mono); font-size:12px; letter-spacing:.18em;
    text-transform:uppercase; color:var(--teal); margin:0 0 10px; }}
  h1 {{ font-size:30px; line-height:1.15; margin:0 0 8px; font-weight:650;
    text-wrap:balance; letter-spacing:-.01em; }}
  .lede {{ color:var(--muted); margin:0 0 28px; max-width:64ch; }}
  .scroll {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; margin:0 0 14px;
    font-family:var(--mono); font-size:13px; font-variant-numeric:tabular-nums; }}
  caption {{ text-align:left; font-family:var(--mono); font-size:12px;
    letter-spacing:.14em; text-transform:uppercase; color:var(--muted);
    padding-bottom:8px; }}
  th, td {{ text-align:right; padding:7px 10px; border-bottom:1px solid var(--line); }}
  th:first-child, td:first-child {{ text-align:left; }}
  thead th {{ color:var(--muted); font-weight:600; border-bottom:1.5px solid var(--ink); }}
  .chip {{ display:inline-block; width:11px; height:11px; border-radius:2px;
    margin-right:8px; }}
  .defs {{ list-style:none; padding:0; margin:0 0 8px; font-size:12px;
    color:var(--muted); display:grid; grid-template-columns:repeat(2,1fr);
    gap:3px 28px; }}
  .defs b {{ color:var(--ink); font-weight:600; font-family:var(--mono); }}
  .legend {{ display:flex; flex-wrap:wrap; gap:22px; align-items:center;
    margin:22px 0 14px; font-family:var(--mono); font-size:13px; color:var(--muted); }}
  .legend .key {{ display:inline-block; width:22px; height:3px; border-radius:2px;
    margin-right:8px; vertical-align:middle; }}
  .grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:18px; }}
  .trio {{ display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }}
  .card {{ margin:0; background:var(--panel); border:1px solid var(--line);
    border-radius:6px; padding:14px 14px 6px; }}
  .card figcaption {{ font-size:14px; font-weight:600; margin-bottom:4px; }}
  .card svg {{ width:100%; height:auto; display:block; }}
  .viewer {{ width:100%; aspect-ratio:1/1; display:block; background:var(--ground);
    border:1px solid var(--line); border-radius:4px; cursor:grab; touch-action:none; }}
  .viewer:active {{ cursor:grabbing; }}
  .card .note {{ font-size:12px; color:var(--muted); margin:6px 2px 2px; }}
  h2 {{ font-size:18px; font-weight:650; margin:30px 0 10px; }}
  h3 {{ font-family:var(--mono); font-size:12px; letter-spacing:.1em;
    text-transform:uppercase; color:var(--muted); margin:0 0 6px; }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; align-items:start; }}
  .cols > div {{ min-width:0; }}
  pre {{ margin:0; background:var(--panel); border:1px solid var(--line);
    border-radius:6px; padding:12px 14px; font-family:var(--mono); font-size:12px;
    line-height:1.5; overflow-x:auto; white-space:pre-wrap; overflow-wrap:anywhere;
    color:var(--ink); }}
  .tick {{ font-family:var(--mono); font-size:11px; fill:var(--muted); }}
  .axis {{ font-family:var(--mono); font-size:11px; fill:var(--muted); letter-spacing:.04em; }}
  .limit {{ font-family:var(--mono); font-size:11px; fill:{LIMIT}; font-weight:600; }}
  footer {{ margin-top:30px; padding-top:18px; border-top:1px solid var(--line);
    color:var(--muted); font-size:13px; max-width:72ch; }}
  footer code {{ font-family:var(--mono); font-size:12px; }}
  @media (max-width:860px) {{ .trio {{ grid-template-columns:1fr; }} }}
  @media (max-width:640px) {{ .grid, .cols {{ grid-template-columns:1fr; }} }}
</style>
<div class="wrap">
  <p class="eyebrow">nec2c modeled</p>
  <h1>Eggbeater Performance</h1>
  <p class="lede">Frequency plots overlay each design on offset from its own
  design frequency; the 3 dB axial-ratio band is the binding limit on usable
  coverage. The input spec and physical cut list for each design follow the
  charts.</p>

  <div class="scroll">
  <table>
    <caption>Figures of merit</caption>
    <thead><tr>
      <th>Design</th><th>f0 (MHz)</th><th>feed Z (&#8486;)</th><th>sense</th>
      <th>VSWR (matched)</th><th>AR cone (dB)</th><th>cov gain (dBi)</th>
      <th>2:1 VSWR band</th><th>3 dB AR band</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
  <ul class="defs">
    <li><b>feed Z</b> &mdash; predicted feedpoint impedance, before matching</li>
    <li><b>sense</b> &mdash; circular-polarization handedness (RHCP / LHCP)</li>
    <li><b>VSWR (matched)</b> &mdash; standing-wave ratio at 50 ohm after the
      match network</li>
    <li><b>AR cone</b> &mdash; mean axial ratio within 30 deg of zenith
      (0 dB = perfect circular)</li>
    <li><b>cov gain</b> &mdash; worst-case gain within 60 deg of zenith
      (elevation &ge; 30 deg)</li>
    <li><b>2:1 VSWR band</b> &mdash; span where matched VSWR stays under 2</li>
    <li><b>3 dB AR band</b> &mdash; span where axial ratio stays under 3 dB
      (usable CP coverage)</li>
  </ul>

  <div class="legend">{legend}</div>
  <div class="grid">{charts}</div>

  <p class="eyebrow" style="margin-top:38px">Geometry and sky coverage</p>
  <p class="lede">The wire model and the gain and axial-ratio maps over the whole
  upper hemisphere for each design. The maps are polar: overhead at the centre,
  the horizon at the rim, azimuth around. Near-omnidirectional designs read as
  smooth rings; reflector asymmetry shows up as azimuth ripple.</p>
  {spatial}

  <p class="eyebrow" style="margin-top:38px">Design details</p>
  {details}

  <footer>
    Axial ratio is averaged over the high-elevation cone for the table and taken
    on the &phi;=0 principal plane for the elevation cut. The 2:1 VSWR band
    assumes an idealized lossless match, so treat the narrower 3 dB axial-ratio
    band as operational coverage. Modeled with <code>nec2c</code>; near-linear
    horizon values are clamped at 10 dB so traces stay on-axis.
  </footer>
</div>
{viewer}
"""
