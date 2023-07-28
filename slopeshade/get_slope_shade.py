import json
import subprocess
import os
import glob
from pathlib import Path


import wget
from pyproj import Transformer
import requests

QGIS_BIN_PATH = "/Applications/QGIS.app/Contents/MacOS/bin/"

def pasted_to_bbox(y1, x1, y2, x2):
    ulx = min(x1, x2)
    uly = max(y1, y2)
    lrx = max(x1, x2)
    lry = min(y1, y2)
    return f"{ulx}, {uly}, {lrx}, {lry}"

def transform_bbox(bbox):
    pts = bbox.split(',')
    pts_ordered = [(pts[0], pts[1]),(pts[2], pts[3])]
    transformer = Transformer.from_crs("WGS 84", "EPSG:26911")
    tformed = ()
    for pair in pts_ordered:
        tformed += transformer.transform(pair[1],pair[0])

    x1, y1, x2, y2 = tformed
    return f"{x1}, {x2}, {y1}, {y2} [EPSG:26911]"


def download_dems(bounding_box):
    data_dir = Path("./source_dems/")
    data_dir.mkdir(exist_ok=True)

    opr_dataset = "Original%20Product%20Resolution%20(OPR)%20Digital%20Elevation%20Model%20(DEM)"
    dem_1m_dataset = "Digital%20Elevation%20Model%20(DEM)%201%20meter"
    for dataset in [opr_dataset, dem_1m_dataset]:
        url = f"https://tnmaccess.nationalmap.gov/api/v1/products?&datasets={dataset}&bbox={bounding_box}&prodFormats=&max=1000&offset=0"
        
        try:
            result = requests.get(url=url, timeout=5)
        except requests.exceptions.ReadTimeout:
            print(f"{url} failed to elicit a reply")
            raise
        results = [(item['title'], item['downloadURL']) for item in json.loads(result.text)["items"]]
        if len(results) > 0: break
    
    # check total download size to make sure we aren't accidentally overloading the servers
    tot_size = 0
    MAX_DL_SIZE = 3000 # in megabytes
    for result in results:
        response = requests.head(result[1], allow_redirects=True)
        size = int(response.headers.get('content-length', -1), )
        tot_size += size
    tot_size = tot_size / float(1 << 20) # convert to MB
    if tot_size > MAX_DL_SIZE:
        raise ValueError(f'Asking for {tot_size} MB, be kind to our poor government servers')
    
    filenames = []
    # download results
    for result in results:
        url = result[1]
        filepath = data_dir.joinpath(url.split('/')[-1])
        if not filepath.exists(): #check if already downloaded
            wget.download(url, out=str(filepath))
        filenames.append(str(filepath))

    return filenames

def get_slope_raster(bounding_box, outfilename="out.tif", delete_intermediates=True, arg_method="GDAL_PYTHON"):
    """ Download and create a slope raster for a given bounding box
    Args:
        bounding_box (str): bounding box in comma+space separated ulx, uly, lrx, lry format. 
        outfilename (str): outfilename
        delete_intermediates (bool): delete all but output file and source DEMs
        arg_method (str): method for calling GDAL binaries. Valid: ["QGIS_PROCESS", "GDAL_PYTHON", "GDAL_BIN"]
    """
    
    if arg_method == "GDAL_PYTHON":
        from osgeo_utils.gdal_merge import gdal_merge
        from osgeo import gdal

    filenames = download_dems(bounding_box)

    # join all rasters
    if len(filenames) == 0:
        raise ValueError("No source data found for bounding box")
    elif len(filenames) == 1:
        outfile = filenames[0] # only one, no need to join
    else:
        outfile = "1-joined.tif"
        
        if arg_method == "QGIS_PROCESS":
            inputs = [] 
            for filename in filenames:
                inputs.append(f"--INPUT={filename}")
            join_command = f"""{QGIS_BIN_PATH}qgis_process run gdal:merge \
                --distance_units=meters \
                --area_units=m2 \
                --ellipsoid=EPSG:7019  \
                {" ".join(inputs)} \
                --OUTPUT={outfile} """
            subprocess.call(join_command, shell=True)
        elif arg_method == "GDAL_BIN":
            join_command = f"{QGIS_BIN_PATH}gdal_merge.py -o {outfile} {' '.join(filenames)}"
            subprocess.call(join_command, shell=True)
        elif arg_method == "GDAL_PYTHON":
            join_command = f" -o {outfile} {' '.join(filenames)}".split(' ')
            gdal_merge(join_command)

            
    # crop
    infile = outfile
    outfile = "2-cropped.tif"

    if arg_method == "QGIS_PROCESS":
        bounds = transform_bbox(bounding_box)
        clip_command = f"""{QGIS_BIN_PATH}qgis_process run gdal:cliprasterbyextent \
            --distance_units=meters \
            --area_units=m2 \
            --ellipsoid=EPSG:7019  \
            --INPUT={infile} \
            --PROJWIN="{bounds}" \
            --OUTPUT={outfile}"""
        subprocess.call(clip_command, shell=True)
    elif arg_method == "GDAL_BIN":
        clip_command = f"{QGIS_BIN_PATH}gdal_translate -projwin {bounding_box} -projwin_srs WGS84 {infile} {outfile}"
        subprocess.call(clip_command, shell=True)
    elif arg_method == "GDAL_PYTHON":
        gdal.Translate(outfile, infile, projWin=bounding_box.split(', '), projWinSRS="WGS84")#, outputSRS="EPSG:6318")

    if delete_intermediates:
        if len(filenames) != 1: #don't want to delete source data if we didn't merge
            os.remove(infile)
    
    # slope shade
    infile = outfile
    outfile = "3-slope.tif"

    if arg_method == "QGIS_PROCESS":
        slope_command = f"""{QGIS_BIN_PATH}qgis_process run gdal:slope \
            --distance_units=meters\
            --area_units=m2 \
            --ellipsoid=EPSG:7019 \
            --BAND=1 \
            --INPUT='{infile}'\
            --OUTPUT={outfile}"""
        subprocess.call(slope_command, shell=True)
    elif arg_method == "GDAL_BIN":
        slope_command = f"""{QGIS_BIN_PATH}gdaldem slope {infile} {outfile}"""
        subprocess.call(slope_command, shell=True)
    elif arg_method == "GDAL_PYTHON":
        gdal.DEMProcessing(outfile, infile, processing="slope")

    if delete_intermediates:
        os.remove(infile)
    
    # recolor
    infile = outfile
    outfile = outfilename
    caltopo_color = """0 255 255 255 255 0.3023
    20 146 240 1 255 19.1819
    30 255 212 1 255 28.2829
    40 255 49 1 255 38.7392
    50 152 15 117 255 49.1956
    68 19 1 158 255 67.4943
    80 0 0 0 255 79.8871
    """
    color_table = "col.txt"
    with open(color_table, 'w') as colfile:
        colfile.writelines(caltopo_color)
    
    if arg_method == "QGIS_PROCESS":
        recolor_command = f"""{QGIS_BIN_PATH}qgis_process run gdal:colorrelief \
            --distance_units=meters \
            --area_units=m2 \
            --ellipsoid=EPSG:7019 \
            --BAND=1 \
            --INPUT={infile} \
            --COLOR_TABLE={color_table} \
            --OUTPUT={outfile}"""
        subprocess.call(recolor_command, shell=True)
    elif arg_method == "GDAL_BIN":
        recolor_command = f"{QGIS_BIN_PATH}gdaldem color-relief {infile} {color_table} {outfile}"
        subprocess.call(recolor_command, shell=True)
    elif arg_method == "GDAL_PYTHON":
        gdal.DEMProcessing(outfile, infile, processing="color-relief", colorFilename=color_table)

    if delete_intermediates:
        os.remove(infile)
        os.remove(color_table)

    # delete aux files 
    for f in glob.glob(f"*.aux.xml"):
        os.remove(f)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        coords = list(map(float, sys.argv[1].split(',')))
    else:
        coord1 = input("Enter first bounding box coodinate: ")
        coord2 = input("Enter second bounding box coordinate: ")
        coords = list(map(float, (coord1 + ',' + coord2).split(',')))
    assert len(coords) == 4
    bbox = pasted_to_bbox( *coords)
    print(bbox)
    get_slope_raster(bbox, delete_intermediates=True, arg_method="GDAL_PYTHON")