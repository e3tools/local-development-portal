function loadGeoJsonMap(url, access_token) {
    mapboxgl.accessToken = access_token;

    fetch(url)
    .then(response => response.json())
    .then(data => {

        let map_spin = $('.map-spin');
        let regions_spin = $('#regions-nav-link .overlay');
        let regions_angle = $('#regions-nav-link .fa-angle-left');
        let sidebar_back = $('#sidebar_back');
        let load_percentage = $('#load-percentage');
        let map_message = $('#map-message');
        let around_africa_id = 'around_africa';

        function calculateBoundingBox(geojson) {
            var minX = geojson.features[0].geometry.coordinates[0][0][0];
            var minY = geojson.features[0].geometry.coordinates[0][0][1];
            var maxX = geojson.features[0].geometry.coordinates[0][1][0];
            var maxY = geojson.features[0].geometry.coordinates[0][1][1];
            geojson.features.forEach(function (feature) {
                feature.geometry.coordinates[0].forEach(function (coordinate) {
                    if (!minX || coordinate[0] < minX) minX = coordinate[0];
                    if (!minY || coordinate[1] < minY) minY = coordinate[1];
                    if (!maxX || coordinate[0] > maxX) maxX = coordinate[0];
                    if (!maxY || coordinate[1] > maxY) maxY = coordinate[1];
                });
            });

            return [[minX, minY], [maxX, maxY]];
        }

        function clearAllTimeout() {
            let id = window.setTimeout(function () {
            }, 0);

            while (id--) {
                window.clearTimeout(id); // will do nothing if no timeout with id is present
            }
        }

        function enableElements() {
            clearAllTimeout();
            if (map_message.html()) {
                setTimeout(function () {
                    map_message.html('').hide();
                    map_spin.hide();
                }, 2000);
            } else {
                map_spin.hide();
                map_message.hide();
            }
            sidebar_back.removeClass('disabled');
            load_percentage.html('');
        }

        var geoJson = {
            "type": "FeatureCollection",
            "features": data.features
        };
        var bbox = calculateBoundingBox(geoJson);
        const mymap = new mapboxgl.Map({
            container: 'mapid',
            style: 'mapbox://styles/jorgedavidgb/cktwydyi118en18l9alhtk5ds',
        });

        mymap.fitBounds(bbox);

        mymap.on('load', () => {
            mymap.dragRotate.disable();

            mymap.addSource(around_africa_id, {
                'type': 'geojson',
                'data': geoJson
            });

            mymap.addLayer({
                'id': around_africa_id,
                'type': 'fill',
                'source': around_africa_id,
                'layout': {},
                'paint': {
                    'fill-color': '#ed78b3',
                    'fill-opacity': 0.5
                }
            });

            $('#legend').append('<i class="nav-icon fa fa-square-full" style="color: #ed78b3"></i> <span>Togo</span>');
        });

        regions_angle.hide();
        regions_spin.show();

        mymap.on('load', (e) => {
            setTimeout(function () {
                map_spin.hide();
                map_message.hide();
            }, 1000);
        });

        mymap.on('idle', (e) => {
            setTimeout(function () {
                enableElements();
            }, 1000);
        });

    });
}
