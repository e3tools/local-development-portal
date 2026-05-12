/**
 * canton_map.js
 * =============
 * Mapbox GL JS controller for the Canton Profile – Map tab.
 *
 * Responsibilities:
 *  - Initialize the map centred on canton bounds.
 *  - Manage three exclusive layers: "priorities", "subprojects", "planning".
 *  - Render popups appropriate to the active layer on marker click.
 *  - Update the legend when the active layer changes.
 *  - Pan/zoom when the user clicks a sidebar subproject item.
 *
 * Dependencies (loaded by the template):
 *  - mapbox-gl-js  v3.x
 *  - CANTON_MAP_DATA  (window global injected via <script> in the template)
 *
 * Usage: included via {% static 'js/canton_map.js' %}
 */

(function () {
    "use strict";

    // -------------------------------------------------------------------------
    // Constants
    // -------------------------------------------------------------------------
    const LAYER_PRIORITIES = "priorities";
    const LAYER_SUBPROJECTS = "subprojects";
    const LAYER_PLANNING = "planning";

    const DEFAULT_ZOOM = 10;
    const MARKER_RADIUS = 8;   // px – priorities / planning circle radius
    const SUB_RADIUS = 14;  // px – subprojects ring outer radius

    // Planning colors (must match canton_map_service.py)
    const PLANNING_COLORS = {
        "completed": "#22C55E",
        "in progress": "#EAB308",
        "not started": "#EF4444",
    };

    // Keep a reference to the currently open popup so we can close it on layer switch.
    let _activePopup = null;

    // -------------------------------------------------------------------------
    // Bootstrap
    // -------------------------------------------------------------------------
    // Support both DOMContentLoaded (tab already open) and
    // the lazy 'cantonMapTabShown' event (tab opened later).
    function tryInit() {
        if (!window.CANTON_MAP_DATA || !window.MAPBOX_TOKEN) return;
        initCantonMap(window.CANTON_MAP_DATA, window.MAPBOX_TOKEN);
    }

    document.addEventListener("DOMContentLoaded", function () {
        // Only auto-init if the map tab is the default active one
        var activePane = document.querySelector('.tab-pane.active #canton-map');
        if (activePane) tryInit();
    });
    document.addEventListener("cantonMapTabShown", function() {
        tryInit();
    });

    // If script is loaded dynamically (HTMX), and tab is already active
    if (document.readyState !== "loading") {
        var activePane = document.querySelector('.tab-pane.active #canton-map');
        if (activePane) tryInit();
    }

    // -------------------------------------------------------------------------
    // Initialization
    // -------------------------------------------------------------------------
    function initCantonMap(data, token) {
        mapboxgl.accessToken = token;

        const map = new mapboxgl.Map({
            container: "canton-map",
            style: "mapbox://styles/mapbox/streets-v11",
            zoom: DEFAULT_ZOOM,
        });

        // Fit to canton bounds if available
        if (data.bounds) {
            map.fitBounds(data.bounds, {padding: 40, animate: false});
        } else {
            // Fallback: centre on first feature with coordinates
            const first = data.features.find(f => f.latitude && f.longitude);
            if (first) {
                map.setCenter([first.longitude, first.latitude]);
            }
        }

        map.addControl(new mapboxgl.NavigationControl(), "top-right");

        map.on("load", function () {
            addSources(map, data.features);
            addLayers(map);
            bindLayerEvents(map);
            renderSidebar(data.subprojects, map);
            setActiveLayer(map, LAYER_PRIORITIES);   // default layer
        });
    }

    // -------------------------------------------------------------------------
    // GeoJSON sources
    // -------------------------------------------------------------------------
    function buildGeoJSON(features) {
        return {
            type: "FeatureCollection",
            features: features
                .filter(f => f.latitude != null && f.longitude != null)
                .map(f => ({
                    type: "Feature",
                    geometry: {
                        type: "Point",
                        coordinates: [f.longitude, f.latitude],
                    },
                    properties: f,
                })),
        };
    }

    function addSources(map, features) {
        map.addSource("villages", {type: "geojson", data: buildGeoJSON(features)});
    }

    // -------------------------------------------------------------------------
    // Layer definitions
    // -------------------------------------------------------------------------
    function addLayers(map) {
        // --- PRIORITIES layer ---
        // Solid circle colored by category (or grey if no priority)
        map.addLayer({
            id: LAYER_PRIORITIES,
            type: "circle",
            source: "villages",
            paint: {
                "circle-radius": [
                    "case", ["get", "has_priority"], MARKER_RADIUS + 2, MARKER_RADIUS - 2,
                ],
                // priority_color already set to NO_PRIORITY_COLOR when no priority exists
                "circle-color": ["get", "priority_color"],
                "circle-stroke-width": 1.5,
                "circle-stroke-color": "#ffffff",
                "circle-opacity": 1,
            },
        });

        // --- SUBPROJECTS layer ---
        // Semi-transparent rings, category color
        map.addLayer({
            id: LAYER_SUBPROJECTS,
            type: "circle",
            source: "villages",
            filter: ["==", ["get", "has_subprojects"], true],
            paint: {
                "circle-radius": SUB_RADIUS,
                // Use sub_category_color for the subprojects ring
                "circle-color": ["get", "sub_category_color"],
                "circle-opacity": 0.30,
                "circle-stroke-width": 3,
                "circle-stroke-color": ["get", "sub_category_color"],
                "circle-stroke-opacity": 0.85,
            },
        });

        // --- PLANNING layer ---
        // All villages coloured by task completion (green / yellow / red)
        map.addLayer({
            id: LAYER_PLANNING,
            type: "circle",
            source: "villages",
            paint: {
                "circle-radius": MARKER_RADIUS + 1,
                "circle-color": ["get", "planning_color"],
                "circle-stroke-width": 2,
                "circle-stroke-color": "#ffffff",
                "circle-opacity": 0.9,
            },
        });

        // --- Village name labels (always visible) ---
        map.addLayer({
            id: "village-labels",
            type: "symbol",
            source: "villages",
            layout: {
                "text-field": ["get", "name"],
                "text-size": 11,
                "text-anchor": "top",
                "text-offset": [0, 0.8],
                "text-allow-overlap": false,
            },
            paint: {
                "text-color": "#374151",
                "text-halo-color": "#ffffff",
                "text-halo-width": 1.5,
            },
        });
    }

    // -------------------------------------------------------------------------
    // Layer toggle  (closes the active popup)
    // -------------------------------------------------------------------------
    function setActiveLayer(map, layerId) {
        // Close any open popup
        if (_activePopup) {
            _activePopup.remove();
            _activePopup = null;
        }

        [LAYER_PRIORITIES, LAYER_SUBPROJECTS, LAYER_PLANNING].forEach(function (id) {
            map.setLayoutProperty(id, "visibility", id === layerId ? "visible" : "none");
        });

        document.querySelectorAll(".map-layer-btn").forEach(function (btn) {
            var isActive = btn.dataset.layer === layerId;
            btn.classList.toggle("btn-primary", isActive);
            btn.classList.toggle("btn-outline-secondary", !isActive);
        });

        updateLegend(layerId);
    }

    // -------------------------------------------------------------------------
    // Popups
    // -------------------------------------------------------------------------
    function bindLayerEvents(map) {
        var activeLayer = LAYER_PRIORITIES;

        // Store current active layer for popup logic
        document.querySelectorAll(".map-layer-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                activeLayer = this.dataset.layer;
                setActiveLayer(map, activeLayer);
            });
        });

        [LAYER_PRIORITIES, LAYER_SUBPROJECTS, LAYER_PLANNING].forEach(function (layerId) {
            map.on("mouseenter", layerId, function () {
                map.getCanvas().style.cursor = "pointer";
            });
            map.on("mouseleave", layerId, function () {
                map.getCanvas().style.cursor = "";
            });

            map.on("click", layerId, function (e) {
                if (!e.features.length) return;
                var props = e.features[0].properties;
                var coords = e.features[0].geometry.coordinates.slice();

                // Close previous popup before opening a new one
                if (_activePopup) {
                    _activePopup.remove();
                }

                _activePopup = new mapboxgl.Popup({maxWidth: "290px"})
                    .setLngLat(coords)
                    .setHTML(buildPopupHTML(props, layerId))
                    .addTo(map);
            });
        });
    }

    function buildPopupHTML(props, layerId) {
        const strings = window.MAP_STRINGS || {};
        // Mapbox serializes all property values as strings; parse booleans/objects back.
        function safe(key) {
            var v = props[key];
            if (v === "true" || v === true) return true;
            if (v === "false" || v === false) return false;
            return v;
        }

        var html = `<div class="canton-map-popup">
        <h6 class="font-weight-bold mb-1">${props.name || ""}</h6>
        <small class="text-muted">Pop. ${Number(props.population || 0).toLocaleString()}</small>
        <hr class="my-1">`;

        if (layerId === LAYER_PRIORITIES) {
            if (safe("has_priority")) {
                var catName = props.category_name || "";
                var catColor = props.priority_color || "#6B7280";
                var priority = props.top_priority;
                if (typeof priority === "string") {
                    try {
                        priority = JSON.parse(priority);
                    } catch (_) {
                        priority = null;
                    }
                }
                html += '<div class="d-flex align-items-center mb-1">'
                    + '<span class="badge mr-2" style="background:' + catColor + ';color:#fff;font-size:.75rem">'
                    + catName + '</span></div>';
                if (priority && priority.title) {
                    html += '<div style="font-size:.85rem">' + priority.title + '</div>';
                    if (priority.cost) {
                        html += '<div class="text-muted" style="font-size:.8rem">'
                            + Number(priority.cost).toLocaleString() + ' FCFA</div>';
                    }
                }
            } else {
                html += '<div class="text-muted font-italic" style="font-size:.85rem">' + (strings.noPriority || "No priority identified") + '</div>';
            }
        }

        if (layerId === LAYER_SUBPROJECTS) {
            var count = Number(props.subprojects_count || 0);
            var catN = props.sub_category_name || "";
            var catC = props.sub_category_color || "#6B7280";
            var subprojectLabel = count !== 1 ? (strings.activeSubprojects || "active sub-projects") : (strings.activeSubproject || "active sub-project");
            html += '<div style="font-size:.85rem"><strong>' + count + '</strong> ' + subprojectLabel + '</div>';
            if (catN) {
                html += '<span class="badge mt-1" style="background:' + catC + ';color:#fff;font-size:.75rem">'
                    + catN + '</span>';
            }
        }

        if (layerId === LAYER_PLANNING) {
            var status = props.planning_status || "not started";
            var label = {
                "completed": strings.completed || "Completed",
                "in progress": strings.inProgress || "In Progress",
                "not started": strings.notStarted || "Not Started"
            }[status] || status;
            var phases = Number(props.phases_total || 0);
            var done = Number(props.phases_complete || 0);
            html += '<div class="d-flex align-items-center">'
                + '<span class="badge" style="background:' + props.planning_color + ';color:#fff;min-width:90px">'
                + label + '</span></div>'
                + '<div class="mt-1 text-muted" style="font-size:.8rem">'
                + done + ' / ' + phases + ' ' + (strings.phasesComplete || "phases complete") + '</div>';
        }

        html += "</div>";
        return html;
    }

    // -------------------------------------------------------------------------
    // Legend  (uses category_legend from CANTON_MAP_DATA)
    // -------------------------------------------------------------------------
    function updateLegend(layerId) {
        var container = document.getElementById("map-legend-content");
        if (!container) return;

        const strings = window.MAP_STRINGS || {};
        var html = "";

        if (layerId === LAYER_PRIORITIES) {
            // "No priority" entry always first
            html += legendItem(/* NO_PRIORITY_COLOR */ "#9CA3AF", strings.noPriorityLegend || "No priority", false);
            var entries = window.CANTON_MAP_DATA.category_legend || [];
            entries.forEach(function (e) {
                html += legendItem(e.color, e.name, false);
            });
        }

        if (layerId === LAYER_SUBPROJECTS) {
            html += '<div class="text-muted mb-1"><small>' + (strings.onlyVillagesWithSubprojects || "Only villages with active subprojects shown") + '</small></div>';
            var entries = window.CANTON_MAP_DATA.category_legend || [];
            entries.forEach(function (e) {
                html += legendItem(e.color, e.name, true);
            });
        }

        if (layerId === LAYER_PLANNING) {
            html += legendItem(PLANNING_COLORS["completed"], strings.completed || "Completed", false);
            html += legendItem(PLANNING_COLORS["in progress"], strings.inProgress || "In Progress", false);
            html += legendItem(PLANNING_COLORS["not started"], strings.notStarted || "Not Started", false);
        }

        container.innerHTML = html;
    }

    function legendItem(color, label, ring) {
        var style = ring
            ? "width:14px;height:14px;border-radius:50%;border:3px solid " + color + ";background:transparent;opacity:.85;"
            : "width:14px;height:14px;border-radius:50%;background:" + color + ";";
        return '<div class="d-flex align-items-center mb-1">'
            + '<span style="' + style + 'display:inline-block;flex-shrink:0;" class="mr-2"></span>'
            + '<small>' + label + '</small></div>';
    }

    // -------------------------------------------------------------------------
    // Sidebar  (category badge + sector name matching the prototype)
    // -------------------------------------------------------------------------
    function renderSidebar(subprojects, map) {
        var list = document.getElementById("map-subprojects-list");
        if (!list) return;

        const strings = window.MAP_STRINGS || {};

        if (!subprojects || subprojects.length === 0) {
            list.innerHTML = '<p class="text-muted p-2"><small>' + (strings.noInvestmentsFound || "No investments found in this canton.") + '</small></p>';
            return;
        }

        list.innerHTML = subprojects.map(function (s) {
            var catColor = s.category_color || "#6B7280";
            var catName = s.category_name || "";
            var cost = Number(s.estimated_cost || 0).toLocaleString();
            var isSub = s.project_status !== "N";
            var badgeText = isSub ? (strings.subproject || "Subproject") : (strings.priority || "Priority");
            var badgeClass = isSub ? "badge-info" : "badge-secondary";
            var hasCoords = s.latitude != null && s.longitude != null;
            var rankInfo = s.ranking ? '<span class="mr-2" style="font-size:.65rem;color:#6B7280">#' + s.ranking + '</span>' : '';
            var isTopPriority = !isSub && s.ranking === s.village_top_priority_rank;
            var itemClass = isTopPriority ? "bg-white shadow-sm border" : "bg-light";

            return '<div class="map-sidebar-item p-2 mb-1 rounded ' + itemClass + '"'
                + ' style="border-left:4px solid ' + catColor + ';cursor:' + (hasCoords ? 'pointer' : 'default') + ';"'
                + ' data-lng="' + s.longitude + '" data-lat="' + s.latitude + '"'
                + ' data-village="' + s.village_name + '">'
                + '<div class="d-flex align-items-start justify-content-between">'
                + '  <span class="font-weight-bold" style="font-size:.85rem">' + s.village_name + '</span>'
                + '  <div class="d-flex flex-column align-items-end">'
                + '    <span class="badge" style="background:' + catColor + ';color:#fff;font-size:.65rem;white-space:nowrap;margin-bottom:2px">' + catName + '</span>'
                + '    <span class="badge ' + badgeClass + '" style="font-size:.6rem">' + badgeText + '</span>'
                + '  </div>'
                + '</div>'
                + '<div class="text-muted" style="font-size:.8rem;line-height:1.2;margin-top:2px">' + (s.title || "") + '</div>'
                + '<div class="d-flex justify-content-between mt-1 align-items-center">'
                + '  <div class="d-flex align-items-center">' + rankInfo + '<div style="font-size:.75rem;color:#6B7280">' + cost + ' FCFA</div></div>'
                + (!hasCoords ? '  <small class="text-danger" style="font-size:.65rem">' + (strings.noCoords || "No coords") + '</small>' : '')
                + '</div>'
                + '</div>';
        }).join("");

        // Bind click → pan map
        list.querySelectorAll(".map-sidebar-item").forEach(function (item) {
            item.addEventListener("click", function () {
                var lng = parseFloat(this.dataset.lng);
                var lat = parseFloat(this.dataset.lat);
                if (!isNaN(lng) && !isNaN(lat)) {
                    map.flyTo({center: [lng, lat], zoom: 13, duration: 900});

                    // Highlight
                    list.querySelectorAll(".map-sidebar-item").forEach(function (el) {
                        el.classList.remove("bg-light");
                    });
                    this.classList.add("bg-light");
                }
            });
        });
    }

})();