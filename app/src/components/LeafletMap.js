import React, { useEffect, useRef, useMemo } from "react";
import { View, Platform } from "react-native";

// Real Leaflet + OpenStreetMap map (per spec section 9: "Map | Leaflet +
// OpenStreetMap"). On native (iOS/Android) this renders inside a
// react-native-webview WebView. On web (Vercel deployment), react-native-webview
// has no web implementation at all, so this renders a plain <iframe srcDoc=...>
// instead -- same HTML/JS payload, different host element. Avoids
// react-native-maps' dependency on a paid/keyed Google Maps base layer on
// Android, which otherwise renders as a blank black tile with no API key.
//
// The page HTML is built ONCE on mount. Subsequent marker/polyline/center
// changes are pushed into the already-loaded page (injectJavaScript on
// native, direct contentWindow call on web) instead of re-rendering the
// page source, which used to force a full reload (visible flicker) on every
// single GPS tick during LiveRide. See plan item #10.
//
// Props:
//   center: {lat, lon}
//   zoom: number (default 15)
//   markers: [{lat, lon, color, label}]
//   polyline: [{lat, lon}, ...] (optional, drawn as a route line)
//   height: number
//   followCenter: boolean (default true) -- re-pan the map to `center` on update
export default function LeafletMap(props) {
  return Platform.OS === "web" ? <LeafletMapWeb {...props} /> : <LeafletMapNative {...props} />;
}

function LeafletMapNative({ center, zoom = 15, markers = [], polyline = [], height = 240, followCenter = true }) {
  // Lazy require so react-native-webview is never imported in a web bundle.
  const { WebView } = require("react-native-webview");
  const webviewRef = useRef(null);
  const initial = useRef({ center, zoom });
  const latest = useRef({ markers, polyline, center, followCenter });
  latest.current = { markers, polyline, center, followCenter };

  const html = useMemo(
    () => buildHtml(initial.current.center, initial.current.zoom),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  function pushUpdate(m, p, c, f) {
    if (!webviewRef.current) return;
    webviewRef.current.injectJavaScript(updateScript(m, p, c, f));
  }

  useEffect(() => {
    pushUpdate(markers, polyline, center, followCenter);
  }, [markers, polyline, center, followCenter]);

  return (
    <View style={{ height, borderRadius: 14, overflow: "hidden" }}>
      <WebView
        ref={webviewRef}
        originWhitelist={["*"]}
        source={{ html }}
        style={{ flex: 1, backgroundColor: "#eee" }}
        javaScriptEnabled
        domStorageEnabled
        onLoadEnd={() => {
          const l = latest.current;
          pushUpdate(l.markers, l.polyline, l.center, l.followCenter);
        }}
      />
    </View>
  );
}

function LeafletMapWeb({ center, zoom = 15, markers = [], polyline = [], height = 240, followCenter = true }) {
  const iframeRef = useRef(null);
  const initial = useRef({ center, zoom });

  const html = useMemo(
    () => buildHtml(initial.current.center, initial.current.zoom),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  function pushUpdate(m, p, c, f) {
    try {
      const win = iframeRef.current && iframeRef.current.contentWindow;
      if (win && win.abhayaUpdate) win.abhayaUpdate(m, p, c, !!f);
    } catch {
      // Cross-origin or not-yet-loaded -- harmless, onLoad retry covers it.
    }
  }

  useEffect(() => {
    pushUpdate(markers, polyline, center, followCenter);
  }, [markers, polyline, center, followCenter]);

  return (
    <View style={{ height, borderRadius: 14, overflow: "hidden" }}>
      <iframe
        ref={iframeRef}
        srcDoc={html}
        style={{ border: 0, width: "100%", height: "100%" }}
        title="ABHAYA map"
        onLoad={() => pushUpdate(markers, polyline, center, followCenter)}
      />
    </View>
  );
}

function updateScript(m, p, c, f) {
  return `
    (function() {
      if (window.abhayaUpdate) {
        window.abhayaUpdate(${JSON.stringify(m)}, ${JSON.stringify(p)}, ${JSON.stringify(c)}, ${JSON.stringify(!!f)});
      }
      true;
    })();
  `;
}

function buildHtml(center, zoom) {
  const lat = center?.lat ?? 21.1702;
  const lon = center?.lon ?? 72.8311;

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    html, body, #map { height: 100%; margin: 0; padding: 0; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    var map = L.map('map', { zoomControl: false, attributionControl: true }).setView([${lat}, ${lon}], ${zoom});
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    var markerLayer = L.layerGroup().addTo(map);
    var polylineLayer = null;

    // Called from React Native via injectJavaScript (native) or direct
    // contentWindow call (web) on every prop change, instead of reloading
    // this whole page each time.
    window.abhayaUpdate = function(markers, polyline, center, followCenter) {
      markerLayer.clearLayers();
      (markers || []).forEach(function(m) {
        var marker = L.circleMarker([m.lat, m.lon], {
          radius: 8, color: "#ffffff", weight: 2,
          fillColor: m.color || "#8C6FF2", fillOpacity: 1
        });
        if (m.label) marker.bindPopup(m.label);
        marker.addTo(markerLayer);
      });

      if (polylineLayer) { map.removeLayer(polylineLayer); polylineLayer = null; }
      if (polyline && polyline.length > 1) {
        polylineLayer = L.polyline(polyline.map(function(p) { return [p.lat, p.lon]; }), {
          color: "#8C6FF2", weight: 5, opacity: 0.85
        }).addTo(map);
      }

      if (followCenter && center) {
        map.panTo([center.lat, center.lon], { animate: true, duration: 0.4 });
      }
    };

    // Draw the initial state passed at page-build time.
    window.abhayaUpdate(${JSON.stringify([])}, ${JSON.stringify([])}, null, false);
  </script>
</body>
</html>`;
}
