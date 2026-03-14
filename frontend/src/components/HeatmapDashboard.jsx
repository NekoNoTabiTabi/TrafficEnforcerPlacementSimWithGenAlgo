import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";


const API_BASE = "http://localhost:5000";
const ILOILO_CENTER = [122.5621, 10.7202]; // maplibre uses [lng, lat]

export default function HeatmapDashboard() {
    const mapContainer = useRef(null);
    const map = useRef(null);
    const [points, setPoints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [mapReady, setMapReady] = useState(false);

    // Initialize map once
   useEffect(() => {
    if (map.current) return;
    if (!mapContainer.current) return;  // ← wait for ref to be ready

    const initMap = () => {
        map.current = new maplibregl.Map({
            container: mapContainer.current,
            style: {
                version: 8,
                sources: {
                    "osm-tiles": {
                        type: "raster",
                        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                        tileSize: 256,
                        attribution: "© OpenStreetMap contributors",
                    },
                },
                layers: [
                    {
                        id: "osm-tiles",
                        type: "raster",
                        source: "osm-tiles",
                        minzoom: 0,
                        maxzoom: 19,
                    },
                ],
            },
            center: ILOILO_CENTER,
            zoom: 13,
        });

        map.current.on("load", () => {
            map.current.addSource("traffic-heat", {
                type: "geojson",
                data: { type: "FeatureCollection", features: [] },
            });

            map.current.addLayer({
                id: "traffic-heatmap",
                type: "heatmap",
                source: "traffic-heat",
                paint: {
                    "heatmap-weight": [
                        "interpolate", ["linear"],
                        ["get", "congestion"],
                        0, 0, 100, 1,
                    ],
                    "heatmap-intensity": [
                        "interpolate", ["linear"],
                        ["zoom"], 11, 1, 16, 3,
                    ],
                    "heatmap-color": [
                        "interpolate", ["linear"],
                        ["heatmap-density"],
                        0,   "rgba(0,0,0,0)",
                        0.2, "#00cc00",
                        0.4, "#ffff00",
                        0.6, "#ff8800",
                        0.8, "#ff4400",
                        1.0, "#cc0000",
                    ],
                    "heatmap-radius": [
                        "interpolate", ["linear"],
                        ["zoom"], 11, 30, 16, 60,
                    ],
                    "heatmap-opacity": 0.85,
                },
            });

            map.current.addLayer({
                id: "traffic-points",
                type: "circle",
                source: "traffic-heat",
                paint: {
                    "circle-radius": 7,
                    "circle-color": [
                        "interpolate", ["linear"],
                        ["get", "congestion"],
                        0,  "#00cc00",
                        30, "#ffcc00",
                        60, "#ff8800",
                        80, "#cc0000",
                    ],
                    "circle-stroke-color": "#fff",
                    "circle-stroke-width": 1.5,
                    "circle-opacity": 0.9,
                },
            });

            map.current.on("click", "traffic-points", (e) => {
                const props = e.features[0].properties;
                const coords = e.features[0].geometry.coordinates;
                new maplibregl.Popup({ offset: 10 })
                    .setLngLat(coords)
                    .setHTML(`
                        <strong>${props.name}</strong><br/>
                        Congestion: ${props.congestion}%<br/>
                        Speed: ${props.speed} km/h<br/>
                        Priority: ${props.priority}
                    `)
                    .addTo(map.current);
            });

            map.current.on("mouseenter", "traffic-points", () => {
                map.current.getCanvas().style.cursor = "pointer";
            });
            map.current.on("mouseleave", "traffic-points", () => {
                map.current.getCanvas().style.cursor = "";
            });

            setMapReady(true);
        });
    };

    // Small timeout to guarantee DOM is painted before Maplibre tries to attach
    const timer = setTimeout(initMap, 100);

    return () => {
        clearTimeout(timer);
        map.current?.remove();
        map.current = null;
    };
}, []);

    // Update heatmap source whenever points change
    useEffect(() => {
        if (!mapReady || !map.current) return;

        const geojson = {
            type: "FeatureCollection",
            features: points.map((p) => ({
                type: "Feature",
                geometry: {
                    type: "Point",
                    coordinates: [p.lon, p.lat],
                },
                properties: {
                    name: p.name,
                    congestion: p.congestion_level,
                    speed: p.average_speed,
                    priority: p.priority_level,
                },
            })),
        };

        map.current.getSource("traffic-heat")?.setData(geojson);
    }, [points, mapReady]);

    const fetchHeatmap = async () => {
        try {
            setLoading(true);
            const res = await fetch(`${API_BASE}/heatmap/mock`);
            if (!res.ok) throw new Error(`Server error: ${res.status}`);
            const data = await res.json();
            setPoints(data.points);
            setLastUpdated(new Date(data.timestamp).toLocaleTimeString());
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Fetch on mount, then every 5 minutes
    useEffect(() => {
        fetchHeatmap();
        const interval = setInterval(fetchHeatmap, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>

            {/* Header */}
            <div style={{
                padding: "12px 20px",
                background: "#1a1a2e",
                color: "#fff",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexShrink: 0,
            }}>
                <div>
                    <h2 style={{ margin: 0, fontSize: "18px" }}>
                        Iloilo City Traffic Heatmap
                    </h2>
                    <span style={{ fontSize: "12px", color: "#aaa" }}>
                        {lastUpdated ? `Last updated: ${lastUpdated}` : "Fetching data..."}
                    </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    {/* Legend */}
                    <div style={{ display: "flex", gap: "12px", fontSize: "12px" }}>
                        {[
                            { color: "#00cc00", label: "Free (<30%)" },
                            { color: "#ffcc00", label: "Moderate (30-60%)" },
                            { color: "#ff8800", label: "Heavy (60-80%)" },
                            { color: "#cc0000", label: "Gridlock (>80%)" },
                        ].map(({ color, label }) => (
                            <div key={label} style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                                <div style={{ width: 11, height: 11, borderRadius: "50%", background: color }} />
                                <span style={{ color: "#ccc" }}>{label}</span>
                            </div>
                        ))}
                    </div>
                    <button
                        onClick={fetchHeatmap}
                        disabled={loading}
                        style={{
                            padding: "6px 14px",
                            background: loading ? "#444" : "#0066cc",
                            color: "#fff",
                            border: "none",
                            borderRadius: "6px",
                            cursor: loading ? "not-allowed" : "pointer",
                            fontSize: "13px",
                        }}
                    >
                        {loading ? "Refreshing..." : "Refresh"}
                    </button>
                </div>
            </div>

            {/* Error banner */}
            {error && (
                <div style={{
                    background: "#8b0000",
                    color: "#fff",
                    padding: "8px 20px",
                    fontSize: "13px",
                    flexShrink: 0,
                }}>
                    ⚠ {error} — showing last cached data if available.
                </div>
            )}

            {/* Stats bar */}
            {points.length > 0 && (
                <div style={{
                    display: "flex",
                    gap: "24px",
                    padding: "8px 20px",
                    background: "#12122a",
                    color: "#fff",
                    fontSize: "13px",
                    flexShrink: 0,
                }}>
                    <span>Bottlenecks: <strong>{points.length}</strong></span>
                    <span>Free: <strong style={{ color: "#00cc00" }}>
                        {points.filter(p => p.congestion_level < 30).length}
                    </strong></span>
                    <span>Moderate: <strong style={{ color: "#ffcc00" }}>
                        {points.filter(p => p.congestion_level >= 30 && p.congestion_level < 60).length}
                    </strong></span>
                    <span>Heavy: <strong style={{ color: "#ff8800" }}>
                        {points.filter(p => p.congestion_level >= 60 && p.congestion_level < 80).length}
                    </strong></span>
                    <span>Gridlock: <strong style={{ color: "#cc0000" }}>
                        {points.filter(p => p.congestion_level >= 80).length}
                    </strong></span>
                </div>
            )}

            {/* Map */}
            <div
                id= "map"
                ref={mapContainer}
                style={{ flex: 1, width: "100%" }}
            />
        </div>
    );
}