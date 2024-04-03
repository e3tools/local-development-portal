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

        function addLayers(geoJson) {
            const colors = ['#FF6633', '#FFB399', '#FF33FF', '#FFFF99', '#00B3E6',
		  '#E6B333', '#3366E6', '#999966', '#99FF99', '#B34D4D',
		  '#80B300', '#809900', '#E6B3B3', '#6680B3', '#66991A',
		  '#FF99E6', '#CCFF1A', '#FF1A66', '#E6331A', '#33FFCC',
		  '#66994D', '#B366CC', '#4D8000', '#B33300', '#CC80CC',
		  '#66664D', '#991AFF', '#E666FF', '#4DB3FF', '#1AB399',
		  '#E666B3', '#33991A', '#CC9999', '#B3B31A', '#00E680',
		  '#4D8066', '#809980', '#E6FF80', '#1AFF33', '#999933',
		  '#FF3380', '#CCCC00', '#66E64D', '#4D80CC', '#9900B3',
		  '#E64D66', '#4DB380', '#FF4D4D', '#99E6E6', '#6666FF'];

            const clusters = new Set(geoJson.features.map(feature => feature.properties.ClusterID));

            mymap.addSource(around_africa_id, {
                'type': 'geojson',
                'data': geoJson
            });
            clusters.forEach((cluster, index) => {
                mymap.addLayer({
                    'id': cluster.toString(),
                    'type': 'fill',
                    'source': around_africa_id,
                    'layout': {},
                    'paint': {
                        'fill-color': colors[index],
                        'fill-opacity': 0.5
                    },
                    'filter': ['==', 'ClusterID', cluster]
                });
                $('#legend').append(`<i class="nav-icon fa fa-square-full" style=color:${colors[index]}></i> <span>Cluster ${cluster}</span> <br>`);
            })


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

            addLayers(geoJson);
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
