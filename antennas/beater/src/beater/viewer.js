// Interactive 3-D wire-model viewer for the eggbeater performance page.
//
// Self-contained, no library. Each <canvas class="viewer" id="geomN"> has a
// sibling <script type="application/json" id="geomN-data"> holding the tuned
// geometry: { wires: [[x1,y1,z1,x2,y2,z2,colorIndex], ...], feeds: [[x,y,z]] }
// in metres. Drag orbits (yaw/pitch); the wheel zooms. Orthographic, z up.
(function () {
  // Color per wire colorIndex: 0 = loop A, 1 = loop B, 2 = reflector radial.
  var COLORS = ["#0E7C86", "#6D4AA7", "#8A9A96"];
  var FEED = "#B23A48";

  function init(canvas) {
    var src = document.getElementById(canvas.id + "-data");
    if (!src) return;
    var data = JSON.parse(src.textContent);
    var wires = data.wires, feeds = data.feeds, ctx = canvas.getContext("2d");

    // Center on the geometry centroid and scale to the model's bounding radius.
    var pts = [];
    wires.forEach(function (w) { pts.push([w[0], w[1], w[2]], [w[3], w[4], w[5]]); });
    feeds.forEach(function (f) { pts.push(f); });
    var c = [0, 0, 0];
    pts.forEach(function (p) { c[0] += p[0]; c[1] += p[1]; c[2] += p[2]; });
    c = [c[0] / pts.length, c[1] / pts.length, c[2] / pts.length];
    var rad = 1e-6;
    pts.forEach(function (p) {
      rad = Math.max(rad, Math.hypot(p[0] - c[0], p[1] - c[1], p[2] - c[2]));
    });

    var st = { yaw: 0.6, pitch: -0.45, zoom: 1 }, W = 300, H = 300;

    // Yaw about vertical (z), then pitch about screen-x; orthographic project.
    function proj(p) {
      var x = p[0] - c[0], y = p[1] - c[1], z = p[2] - c[2];
      var cy = Math.cos(st.yaw), sy = Math.sin(st.yaw);
      var x1 = x * cy - y * sy, y1 = x * sy + y * cy;
      var cp = Math.cos(st.pitch), sp = Math.sin(st.pitch);
      var depth = y1 * cp - z * sp, up = y1 * sp + z * cp;
      var s = (Math.min(W, H) / 2 - 16) / rad * st.zoom;
      return [W / 2 + x1 * s, H / 2 - up * s, depth];
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      var segs = wires.map(function (w) {
        var a = proj([w[0], w[1], w[2]]), b = proj([w[3], w[4], w[5]]);
        return { a: a, b: b, ci: w[6], d: (a[2] + b[2]) / 2 };
      });
      segs.sort(function (m, n) { return n.d - m.d; }); // far first
      ctx.lineWidth = 1.5;
      ctx.lineCap = "round";
      segs.forEach(function (e) {
        ctx.strokeStyle = COLORS[e.ci] || COLORS[2];
        ctx.beginPath();
        ctx.moveTo(e.a[0], e.a[1]);
        ctx.lineTo(e.b[0], e.b[1]);
        ctx.stroke();
      });
      ctx.fillStyle = FEED;
      feeds.forEach(function (f) {
        var p = proj(f);
        ctx.beginPath();
        ctx.arc(p[0], p[1], 3.6, 0, 6.2832);
        ctx.fill();
      });
    }

    function resize() {
      var dpr = window.devicePixelRatio || 1, css = canvas.clientWidth || 300;
      canvas.width = css * dpr;
      canvas.height = css * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      W = css;
      H = css;
      draw();
    }

    var drag = false, lx = 0, ly = 0;
    canvas.addEventListener("pointerdown", function (e) {
      drag = true; lx = e.clientX; ly = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", function (e) {
      if (!drag) return;
      st.yaw += (e.clientX - lx) * 0.01;
      st.pitch += (e.clientY - ly) * 0.01;
      st.pitch = Math.max(-1.5, Math.min(1.5, st.pitch));
      lx = e.clientX; ly = e.clientY;
      draw();
    });
    canvas.addEventListener("pointerup", function () { drag = false; });
    canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      st.zoom *= e.deltaY < 0 ? 1.1 : 0.9;
      st.zoom = Math.max(0.3, Math.min(6, st.zoom));
      draw();
    }, { passive: false });
    window.addEventListener("resize", resize);
    resize();
  }

  var list = document.querySelectorAll("canvas.viewer");
  for (var i = 0; i < list.length; i++) init(list[i]);
})();
