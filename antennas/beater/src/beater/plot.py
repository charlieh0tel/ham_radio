"""Render eggbeater performance plots as a body-only HTML fragment (inline SVG).

Driven by DesignResult objects; overlays multiple designs per chart.
"""

import html
import json

from .design import (
    AR_TARGET_DB,
    VSWR_LIMIT,
    DesignResult,
    _axial_ratio_db,
    _operating_point,
    analyze,
    bandwidth_within,
    frequency_sweep,
    post_match_vswr,
)
from .nec import RadiationGrid
from .report import format_cut_sheet
from .spec import spec_to_dict

# Data trace colors, cycled per design (teal, amber, violet, green, ...).
TRACE_COLORS = ("#0E7C86", "#C8881C", "#6D4AA7", "#357960", "#B5532A")
LIMIT_COLOR = "#B23A48"
GRID_COLOR = "#DCE3E1"
AXIS_COLOR = "#9FB0AC"

# Fine principal-plane (phi = 0) grid for elevation cuts, theta 0..90 deg.
FINE_GRID = RadiationGrid(ntheta=46, nphi=1, theta0=0.0, phi0=0.0, dtheta=2.0, dphi=0.0)
SWEEP_SPAN_FRACTION = 0.10
SWEEP_POINTS = 61
# Display clamps so near-linear horizon spikes stay on-axis.
AR_CLAMP_DB = 10.0
VSWR_CLAMP = 3.0
GAIN_FLOOR_DB = -50.0

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
        "vswr_post": post_match_vswr(result.z_in),
        "ar_cone": result.ar_boresight_db,
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


def _figure(title, svg):
    return (
        f'<figure class="card"><figcaption>{html.escape(title)}</figcaption>'
        f"{svg}</figure>"
    )


def _band_text(band):
    return "not met" if band is None else f"{band[0]:.1f}&ndash;{band[1]:.1f} MHz"


def _details(results: list[DesignResult]) -> str:
    """Per-design input spec (JSON) and physical cut sheet, as <pre> blocks."""
    blocks = []
    for result in results:
        spec_json = html.escape(json.dumps(spec_to_dict(result.spec), indent=2))
        sheet = html.escape(format_cut_sheet(result))
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
        f"<td>{d['vswr_post']:.2f}</td>"
        f"<td>{d['ar_cone']:.2f}</td>"
        f"<td>{_band_text(d['vswr_band'])}</td>"
        f"<td>{_band_text(d['ar_band'])}</td></tr>"
        for d in data
    )

    return _TEMPLATE.replace("{LIMIT}", LIMIT_COLOR).format(
        rows=rows, legend=legend, charts=charts, details=_details(results)
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
  .legend {{ display:flex; flex-wrap:wrap; gap:22px; align-items:center;
    margin:22px 0 14px; font-family:var(--mono); font-size:13px; color:var(--muted); }}
  .legend .key {{ display:inline-block; width:22px; height:3px; border-radius:2px;
    margin-right:8px; vertical-align:middle; }}
  .grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:18px; }}
  .card {{ margin:0; background:var(--panel); border:1px solid var(--line);
    border-radius:6px; padding:14px 14px 6px; }}
  .card figcaption {{ font-size:14px; font-weight:600; margin-bottom:4px; }}
  .card svg {{ width:100%; height:auto; display:block; }}
  h2 {{ font-size:18px; font-weight:650; margin:30px 0 10px; }}
  h3 {{ font-family:var(--mono); font-size:12px; letter-spacing:.1em;
    text-transform:uppercase; color:var(--muted); margin:0 0 6px; }}
  .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; align-items:start; }}
  pre {{ margin:0; background:var(--panel); border:1px solid var(--line);
    border-radius:6px; padding:12px 14px; font-family:var(--mono); font-size:12px;
    line-height:1.5; overflow-x:auto; color:var(--ink); }}
  .tick {{ font-family:var(--mono); font-size:11px; fill:var(--muted); }}
  .axis {{ font-family:var(--mono); font-size:11px; fill:var(--muted); letter-spacing:.04em; }}
  .limit {{ font-family:var(--mono); font-size:11px; fill:{LIMIT}; font-weight:600; }}
  footer {{ margin-top:30px; padding-top:18px; border-top:1px solid var(--line);
    color:var(--muted); font-size:13px; max-width:72ch; }}
  footer code {{ font-family:var(--mono); font-size:12px; }}
  @media (max-width:640px) {{ .grid, .cols {{ grid-template-columns:1fr; }} }}
</style>
<div class="wrap">
  <p class="eyebrow">nec2c modeled</p>
  <h1>Eggbeater Performance</h1>
  <p class="lede">Frequency plots overlay each design on offset from its own
  design frequency; the 3 dB axial-ratio band is the binding limit on usable
  coverage. The input spec and physical cut list for each design follow the
  charts.</p>

  <table>
    <caption>Figures of merit</caption>
    <thead><tr>
      <th>Design</th><th>f0 (MHz)</th><th>feed Z (&#8486;)</th>
      <th>VSWR (matched)</th><th>AR cone (dB)</th>
      <th>2:1 VSWR band</th><th>3 dB AR band</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <div class="legend">{legend}</div>
  <div class="grid">{charts}</div>

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
"""
