"""
Maps rendering helpers — Google Maps JS API + Folium fallback.
Used by all pages that show maps.
"""
import os
import streamlit as st
import streamlit.components.v1 as components
from typing import List, Optional

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

DARK_MAP_STYLES = """[
  {"elementType":"geometry","stylers":[{"color":"#070e1d"}]},
  {"elementType":"labels.text.fill","stylers":[{"color":"#4a7a98"}]},
  {"elementType":"labels.text.stroke","stylers":[{"color":"#070e1d"}]},
  {"featureType":"road","elementType":"geometry","stylers":[{"color":"#0d1f38"}]},
  {"featureType":"road","elementType":"geometry.stroke","stylers":[{"color":"#0a1628"}]},
  {"featureType":"water","elementType":"geometry","stylers":[{"color":"#050b18"}]},
  {"featureType":"poi","stylers":[{"visibility":"off"}]},
  {"featureType":"transit","stylers":[{"visibility":"off"}]}
]"""


def render_route_map(
    source_lat: float, source_lng: float,
    dest_lat: float, dest_lng: float,
    route_polyline: Optional[str] = None,
    route_points: Optional[List[dict]] = None,
    pickup_lat: Optional[float] = None,
    pickup_lng: Optional[float] = None,
    drop_lat: Optional[float] = None,
    drop_lng: Optional[float] = None,
    height: int = 420,
    title: str = "Route Map",
):
    """Render route map — Google Maps if key available, else Folium."""
    if GOOGLE_MAPS_API_KEY:
        _google_route_map(
            source_lat, source_lng, dest_lat, dest_lng,
            route_polyline, route_points,
            pickup_lat, pickup_lng, drop_lat, drop_lng, height,
        )
    else:
        _folium_route_map(
            source_lat, source_lng, dest_lat, dest_lng,
            route_points, pickup_lat, pickup_lng, drop_lat, drop_lng, height,
        )


def render_live_tracking_map(
    route_points: List[dict],
    driver_lat: float, driver_lng: float,
    source_lat: float, source_lng: float,
    dest_lat: float, dest_lng: float,
    height: int = 500,
):
    """Live tracking map showing driver position on route."""
    if GOOGLE_MAPS_API_KEY:
        _google_live_map(
            route_points, driver_lat, driver_lng,
            source_lat, source_lng, dest_lat, dest_lng, height,
        )
    else:
        _folium_live_map(
            route_points, driver_lat, driver_lng,
            source_lat, source_lng, dest_lat, dest_lng, height,
        )


def render_driver_tracking_sender(
    ride_id: str, token: str, backend_url: str, height: int = 520
):
    """
    JS-powered GPS broadcaster for drivers.
    Uses browser Geolocation API to send position via WebSocket.
    """
    ws_url = backend_url.replace("http://", "ws://").replace("https://", "wss://")

    if GOOGLE_MAPS_API_KEY:
        map_script = f"""
        <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}"></script>
        <script>
        var map, marker;
        function initMap() {{
          map = new google.maps.Map(document.getElementById('driverMap'), {{
            zoom: 15, center: {{lat: 17.385, lng: 78.4867}},
            styles: {DARK_MAP_STYLES}
          }});
          marker = new google.maps.Marker({{
            map: map,
            icon: {{
              path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
              scale: 7, fillColor: '#00d2ff', fillOpacity: 1,
              strokeColor: '#ffffff', strokeWeight: 2
            }}
          }});
        }}
        window.onload = initMap;
        function updateMap(lat, lng) {{
          var pos = {{lat: lat, lng: lng}};
          marker.setPosition(pos);
          map.setCenter(pos);
        }}
        </script>
        """
        map_div = '<div id="driverMap" style="width:100%;height:340px;border-radius:12px;overflow:hidden;"></div>'
    else:
        map_script = ""
        map_div = '<div style="background:#070e1d;border:1px solid #1a3a5c;border-radius:12px;height:200px;display:flex;align-items:center;justify-content:center;color:#4a7a98;font-size:13px;">Map not available — add GOOGLE_MAPS_API_KEY to .env</div>'

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
      body{{margin:0;background:#050b18;color:#e8f4fd;font-family:system-ui,sans-serif;}}
      #statusBar{{padding:8px 16px;background:#0d1f38;border-bottom:1px solid #1a3a5c;display:flex;align-items:center;gap:12px;font-size:12px;}}
      .dot{{width:8px;height:8px;border-radius:50%;background:#00e676;animation:blink 1.2s infinite;flex-shrink:0;}}
      @keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:0.2}}}}
      .chip{{background:#0a1628;border:1px solid #1a3a5c;border-radius:6px;padding:3px 10px;font-size:11px;}}
    </style>
    {map_script}
    </head><body>
    <div id="statusBar">
      <div class="dot" id="dot"></div>
      <span id="statusTxt">Connecting to server...</span>
      <span class="chip" id="speedChip">Speed: -- km/h</span>
      <span class="chip" id="accChip">Accuracy: --m</span>
      <span class="chip" id="sentChip">Sent: 0</span>
    </div>
    {map_div}
    <script>
    var ws, sent = 0, watchId;
    var RIDE_ID = "{ride_id}";
    var TOKEN = "{token}";
    var WS_URL = "{ws_url}/ws/track/" + RIDE_ID + "?token=" + TOKEN + "&role=driver";

    function connect() {{
      ws = new WebSocket(WS_URL);
      ws.onopen = function() {{
        document.getElementById('statusTxt').textContent = 'Broadcasting live location...';
        document.getElementById('dot').style.background = '#00e676';
      }};
      ws.onclose = function() {{
        document.getElementById('statusTxt').textContent = 'Disconnected — reconnecting...';
        document.getElementById('dot').style.background = '#ff416c';
        setTimeout(connect, 3000);
      }};
      ws.onerror = function() {{
        document.getElementById('dot').style.background = '#ffc107';
      }};
      ws.onmessage = function(e) {{
        try {{
          var d = JSON.parse(e.data);
          if (d.type === 'safety_alert') {{
            alert('Safety Alert: ' + d.message);
          }}
        }} catch(err) {{}}
      }};
    }}

    function startGPS() {{
      if (!navigator.geolocation) {{
        document.getElementById('statusTxt').textContent = 'Geolocation not supported';
        return;
      }}
      watchId = navigator.geolocation.watchPosition(function(pos) {{
        var lat = pos.coords.latitude;
        var lng = pos.coords.longitude;
        var speed = pos.coords.speed ? (pos.coords.speed * 3.6).toFixed(1) : '--';
        var acc = pos.coords.accuracy ? pos.coords.accuracy.toFixed(0) : '--';
        document.getElementById('speedChip').textContent = 'Speed: ' + speed + ' km/h';
        document.getElementById('accChip').textContent = 'Accuracy: ' + acc + 'm';
        if (typeof updateMap === 'function') updateMap(lat, lng);
        if (ws && ws.readyState === 1) {{
          ws.send(JSON.stringify({{
            lat: lat, lng: lng,
            speed: pos.coords.speed,
            heading: pos.coords.heading,
            accuracy: pos.coords.accuracy,
            timestamp: new Date().toISOString()
          }}));
          sent++;
          document.getElementById('sentChip').textContent = 'Sent: ' + sent;
        }}
      }}, function(err) {{
        document.getElementById('statusTxt').textContent = 'GPS error: ' + err.message;
      }}, {{enableHighAccuracy: true, maximumAge: 2000, timeout: 5000}});
    }}

    connect();
    startGPS();
    </script>
    </body></html>
    """
    components.html(html, height=height, scrolling=False)


# ── Google Maps implementations ───────────────────────────────────────────────

def _google_route_map(
    src_lat, src_lng, dst_lat, dst_lng,
    polyline, route_points,
    pu_lat, pu_lng, dr_lat, dr_lng, height,
):
    cx = (src_lat + dst_lat) / 2
    cy = (src_lng + dst_lng) / 2

    # Route drawing
    if polyline:
        route_js = f"""
          var decoded = google.maps.geometry.encoding.decodePath("{polyline}");
          new google.maps.Polyline({{
            path: decoded, geodesic: true,
            strokeColor: '#00d2ff', strokeOpacity: 0.9, strokeWeight: 4, map: map
          }});
        """
    elif route_points and len(route_points) >= 2:
        coords = ",".join([f"{{lat:{p['lat']},lng:{p['lng']}}}" for p in route_points])
        route_js = f"""
          new google.maps.Polyline({{
            path: [{coords}], geodesic: true,
            strokeColor: '#00d2ff', strokeOpacity: 0.85, strokeWeight: 4, map: map
          }});
        """
    else:
        route_js = f"""
          var ds = new google.maps.DirectionsService();
          var dr = new google.maps.DirectionsRenderer({{
            map: map, suppressMarkers: true,
            polylineOptions: {{strokeColor: '#00d2ff', strokeWeight: 4, strokeOpacity: 0.9}}
          }});
          ds.route({{
            origin: {{lat:{src_lat},lng:{src_lng}}},
            destination: {{lat:{dst_lat},lng:{dst_lng}}},
            travelMode: 'DRIVING'
          }}, function(res, st) {{ if(st==='OK') dr.setDirections(res); }});
        """

    # Markers
    markers_js = f"""
      new google.maps.Marker({{
        position: {{lat:{src_lat},lng:{src_lng}}}, map: map, title: 'Start',
        icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 10,
                fillColor: '#00e676', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2}}
      }});
      new google.maps.Marker({{
        position: {{lat:{dst_lat},lng:{dst_lng}}}, map: map, title: 'End',
        icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 10,
                fillColor: '#ff416c', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2}}
      }});
    """
    if pu_lat and pu_lng:
        markers_js += f"""
          new google.maps.Marker({{
            position: {{lat:{pu_lat},lng:{pu_lng}}}, map: map, title: 'Your Pickup',
            icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 8,
                    fillColor: '#00d2ff', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2}}
          }});
        """
    if dr_lat and dr_lng:
        markers_js += f"""
          new google.maps.Marker({{
            position: {{lat:{dr_lat},lng:{dr_lng}}}, map: map, title: 'Your Drop',
            icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 8,
                    fillColor: '#a78bfa', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2}}
          }});
        """

    html = f"""
    <html><head><style>body{{margin:0}}#map{{height:{height}px}}</style></head>
    <body><div id="map"></div>
    <script>
    function initMap() {{
      var map = new google.maps.Map(document.getElementById('map'), {{
        center: {{lat:{cx},lng:{cy}}}, zoom: 11,
        styles: {DARK_MAP_STYLES}
      }});
      {route_js}
      {markers_js}
    }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&libraries=geometry&callback=initMap" async defer></script>
    </body></html>
    """
    components.html(html, height=height)


def _google_live_map(
    route_points, drv_lat, drv_lng,
    src_lat, src_lng, dst_lat, dst_lng, height,
):
    if route_points and len(route_points) >= 2:
        coords = ",".join([f"{{lat:{p['lat']},lng:{p['lng']}}}" for p in route_points])
        route_js = f"""
          new google.maps.Polyline({{
            path: [{coords}], geodesic: true,
            strokeColor: '#00d2ff', strokeOpacity: 0.8, strokeWeight: 4,
            strokeDasharray: '8 4', map: map
          }});
        """
    else:
        route_js = ""

    html = f"""
    <html><head><style>body{{margin:0}}#map{{height:{height}px}}</style></head>
    <body><div id="map"></div>
    <script>
    function initMap() {{
      var map = new google.maps.Map(document.getElementById('map'), {{
        center: {{lat:{drv_lat},lng:{drv_lng}}}, zoom: 14,
        styles: {DARK_MAP_STYLES}
      }});
      {route_js}
      new google.maps.Marker({{
        position: {{lat:{src_lat},lng:{src_lng}}}, map: map, title: 'Start',
        icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 9,
                fillColor: '#00e676', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2}}
      }});
      new google.maps.Marker({{
        position: {{lat:{dst_lat},lng:{dst_lng}}}, map: map, title: 'End',
        icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 9,
                fillColor: '#ff416c', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2}}
      }});
      new google.maps.Marker({{
        position: {{lat:{drv_lat},lng:{drv_lng}}}, map: map, title: 'Driver',
        icon: {{path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW, scale: 7,
                fillColor: '#ffc107', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2,
                rotation: 0}}
      }});
    }}
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap" async defer></script>
    </body></html>
    """
    components.html(html, height=height)


# ── Folium fallback implementations ──────────────────────────────────────────

def _folium_route_map(
    src_lat, src_lng, dst_lat, dst_lng,
    route_points, pu_lat, pu_lng, dr_lat, dr_lng, height,
):
    try:
        import folium
        from streamlit_folium import st_folium
        cx = (src_lat + dst_lat) / 2
        cy = (src_lng + dst_lng) / 2
        m = folium.Map(location=[cx, cy], zoom_start=11, tiles="CartoDB dark_matter")
        folium.Marker([src_lat, src_lng], popup="Start",
            icon=folium.Icon(color="green", icon="play")).add_to(m)
        folium.Marker([dst_lat, dst_lng], popup="End",
            icon=folium.Icon(color="red", icon="stop")).add_to(m)
        if pu_lat and pu_lng:
            folium.Marker([pu_lat, pu_lng], popup="Your Pickup",
                icon=folium.Icon(color="blue", icon="user")).add_to(m)
        if dr_lat and dr_lng:
            folium.Marker([dr_lat, dr_lng], popup="Your Drop",
                icon=folium.Icon(color="purple", icon="flag")).add_to(m)
        if route_points and len(route_points) >= 2:
            coords = [[p["lat"], p["lng"]] for p in route_points]
            folium.PolyLine(coords, color="#00d2ff", weight=4, opacity=0.85).add_to(m)
        else:
            folium.PolyLine([[src_lat, src_lng], [dst_lat, dst_lng]],
                color="#00d2ff", weight=3, dash_array="8").add_to(m)
        st_folium(m, height=height, use_container_width=True)
    except ImportError:
        st.info("Install `streamlit-folium` and `folium` for maps: `pip install streamlit-folium folium`")


def _folium_live_map(
    route_points, drv_lat, drv_lng,
    src_lat, src_lng, dst_lat, dst_lng, height,
):
    try:
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[drv_lat, drv_lng], zoom_start=14, tiles="CartoDB dark_matter")
        if route_points and len(route_points) >= 2:
            coords = [[p["lat"], p["lng"]] for p in route_points]
            folium.PolyLine(coords, color="#00d2ff", weight=4, opacity=0.8).add_to(m)
        folium.Marker([src_lat, src_lng], popup="Start",
            icon=folium.Icon(color="green")).add_to(m)
        folium.Marker([dst_lat, dst_lng], popup="End",
            icon=folium.Icon(color="red")).add_to(m)
        folium.Marker([drv_lat, drv_lng], popup="Driver",
            icon=folium.Icon(color="orange", icon="car")).add_to(m)
        st_folium(m, height=height, use_container_width=True)
    except ImportError:
        st.info("Install `streamlit-folium` and `folium` for maps.")
