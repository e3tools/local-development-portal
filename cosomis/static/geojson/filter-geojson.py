togo_outfile = open("togo.geojson", "a")

with open("grid_clusterID.geojson", "r") as file:
    for row in file:
        if "Togo" in row:
            togo_outfile.write(row)
