""" Offline Reverse Geocoder in Python

A Python library for offline reverse geocoding. It improves on an existing library
called reverse_geocode developed by Richard Penman & reverse_geocoder by Ajay Thampi.
"""
from __future__ import print_function

import os
import sys
import csv
csv.field_size_limit(sys.maxsize)
import zipfile
from scipy.spatial import cKDTree as KDTree
from rvgeocoder import cKDTree_MP as KDTree_MP
import numpy as np
import io
from shapely import wkt
from shapely.geometry import Point


GN_URL = 'http://download.geonames.org/export/dump/'
GN_CITIES1000 = 'cities1000'
GN_ADMIN1 = 'admin1CodesASCII.txt'
GN_ADMIN2 = 'admin2Codes.txt'

# Schema of the GeoNames Cities with Population > 1000
GN_COLUMNS = {
    'geoNameId': 0,
    'name': 1,
    'asciiName': 2,
    'alternateNames': 3,
    'latitude': 4,
    'longitude': 5,
    'featureClass': 6,
    'featureCode': 7,
    'countryCode': 8,
    'cc2': 9,
    'admin1Code': 10,
    'admin2Code': 11,
    'admin3Code': 12,
    'admin4Code': 13,
    'population': 14,
    'elevation': 15,
    'dem': 16,
    'timezone': 17,
    'modificationDate': 18
}

# Schema of the GeoNames Admin 1/2 Codes
ADMIN_COLUMNS = {
    'concatCodes': 0,
    'name': 1,
    'asciiName': 2,
    'geoNameId': 3
}

# Schema of the cities file created by this library
RG_COLUMNS = [
    'lat',
    'lon',
    'name',
    'admin1',
    'admin2',
    'cc'
]

# Name of cities file created by this library
RG_FILE = 'rg_cities1000.csv'

# WGS-84 major axis in kms
A = 6378.137

# WGS-84 eccentricity squared
E2 = 0.00669437999014


def singleton(cls):
    """
    Function to get single instance of the RGeocoder class
    """
    instances = {}

    def getinstance(**kwargs):
        """
        Creates a new RGeocoder instance if not created already
        """
        if cls not in instances:
            instances[cls] = cls(**kwargs)
        return instances[cls]
    return getinstance


class RGeocoderDataLoader:
    @classmethod
    def load_files_lines(cls, files: list):
        data_lines = []
        if not files:
            return []
        header_saved = False
        for fl in files:
            with open(fl) as fd:
                # save header only once from the first file
                header = next(fd)
                if not header_saved:
                    data_lines.append(header)
                    header_saved = True
                data_lines.extend(fd.readlines())
        return data_lines

    @classmethod
    def load_files_stream(cls, files: list):
        lines = cls.load_files_lines(files)
        data = ''.join(lines)
        data_stream = io.StringIO(data)
        data_stream.seek(0)
        return data_stream

    @staticmethod
    def _merge_locations(location_files, currect_locations=None):
        common_header = None

        if not currect_locations:
            currect_locations = []
        for loc in location_files:
            with open(loc, 'r') as fd:
                loc_reader = csv.DictReader(fd)
                file_header = loc_reader.fieldnames
                if common_header is None:
                    common_header = file_header
                elif common_header != file_header:
                    raise Exception('File %s has different header than common. Expected header = %s, found = %s' % (
                        loc, common_header, file_header))
                currect_locations.extend(list(loc_reader))
        return currect_locations, common_header

    @staticmethod
    def _remove_polygons_points(locations, polygons_file):
        if not polygons_file:
            return locations

        removed_count = 0
        filtered_locations = []
        polygons = []

        with open(polygons_file, 'r') as fd:
            # get polygons information
            poly_reader = csv.DictReader(fd)
            for row in poly_reader:
                polygons.append((row.get('name', 'unnamed-polygon'),wkt.loads(row['geometry'])))

            # iterate over polygons and remove all points inside of them - avoid collision between sets
            for loc in locations:
                p = Point(float(loc['lon']), float(loc['lat']))
                found = False
                for name, poly in polygons:
                    if poly.contains(p):
                        found = True
                        removed_count += 1
                        print('Removing %s (%s,%s) inside polygon %s' % (
                            loc.get('name', 'unnamed-point'), loc['lat'], loc['lon'], name))
                if not found:
                    filtered_locations.append(loc)
            print('total %s points were removed because found inside patched polygons' % removed_count)
        return filtered_locations

    @classmethod
    def create_patch_locations(cls, location_files: list, patch_loc_file: str,
                               output_file: str = None, patch_poly_file: str = None):
        """ This method recieve a list of location files and two other files describing the patch
        polygon and The points that should represent this polygon in the Spatial index

        REMARK: this can be done much more effiecint and easy using pandas, decided not to use this
        in order to reduce requirements size.
        Arguments:
            location_files {list} -- a csv filename with any schema starting with lat/lon, default is:
                                     lat,lon,name,admin1,admin2,cc
            patch_loc_file {str} -- a csv filename with the same schema as location files
            output_file {str} -- filename for the result of the location files after patching
            patch_poly_file {str} -- OPTIONAL. If given, specifies the a csv file containing polygons of patched
            location and remove all records within these polygon to avoid collision between patch and original 
            location files. schema of file: {cc/name/admin1/admin2}..,geometry(wkt format)
        Returns:
            list of records containing the result of the patched location files
        """

        locations, columns_name = cls._merge_locations(location_files)
        filtered_locations = cls._remove_polygons_points(locations, patch_poly_file)
        new_patched_locations, columns_name = cls._merge_locations([patch_loc_file], filtered_locations)

        if output_file:
            with open(output_file, 'w') as fd:
                writer = csv.DictWriter(fd, fieldnames=columns_name)
                writer.writeheader()
                writer.writerows(new_patched_locations)

        return new_patched_locations


class RGeocoderImpl:
    """
    The main reverse geocoder class
    """
    def __init__(self, mode=2, verbose=True, stream=None, stream_columns=None):
        """ Class Instantiation
        Args:`
        mode (int): Library supports the following two modes:
                    - 1 = Single-threaded K-D Tree
                    - 2 = Multi-threaded K-D Tree (Default)
        verbose (bool): For verbose output, set to True
        stream (io.StringIO): An in-memory stream of a custom data source
        """
        self.mode = mode
        self.verbose = verbose
        if stream:
            coordinates, self.locations = self.load(stream, stream_columns)
        else:
            coordinates, self.locations = self.extract(rel_path(RG_FILE))

        if mode == 1:  # Single-process
            self.tree = KDTree(coordinates)
        else:  # Multi-process
            self.tree = KDTree_MP.cKDTree_MP(coordinates)

    @classmethod
    def from_data(cls, data: str):
        return cls(stream=io.StringIO(data))

    @classmethod
    def from_files(cls, location_files: list):
        """ Loading files data into a stream and creating new instance.
        Arguments:
            location_files {list} -- list of files with lat, lon and additional info on the coord
        Returns:
            [RGeocoderImpl]
        """
        data_stream = RGeocoderDataLoader.load_files_stream(location_files)
        return cls(stream=data_stream)

    def query(self, coordinates):
        """
        Function to query the K-D tree to find the nearest city
        Args:
        coordinates (list): List of tuple coordinates, i.e. [(latitude, longitude)]
        """
        if self.mode == 1:
            _, indices = self.tree.query(coordinates, k=1)
        else:
            _, indices = self.tree.pquery(coordinates, k=1)
        return [self.locations[index] for index in indices]

    def query_dist(self, coordinates):
        """
        Function to query the K-D tree to find the nearest city
        Args:
        coordinates (list): List of tuple coordinates, i.e. [(latitude, longitude)]
        """
        if self.mode == 1:
            dists, indices = self.tree.query(coordinates, k=1)
        else:
            dists, indices = self.tree.pquery(coordinates, k=1)
            # in pquery dists returns a list of arrays so get the first element instead of returning array
            dists = [dist[0] for dist in dists]
        return [(dists[n], self.locations[index]) for (n, index) in enumerate(indices)]

    def load(self, stream, stream_columns):
        """
        Function that loads a custom data source
        Args:
        stream (io.StringIO): An in-memory stream of a custom data source.
                              The format of the stream must be a comma-separated file.
        """
        print('Loading geocoded stream ...')
        stream_reader = csv.DictReader(stream, delimiter=',')
        header = stream_reader.fieldnames

        if stream_columns and header != stream_columns:
            raise csv.Error('Input must be a comma-separated file with header containing ' + \
                'the following columns - %s.\nFound header - %s.\nFor more help, visit: ' % (','.join(stream_columns), ','.join(header)) + \
                'https://github.com/thampiman/reverse-geocoder')

        # Load all the coordinates and locations
        geo_coords, locations = [], []
        for row in stream_reader:
            geo_coords.append((row['lat'], row['lon']))
            locations.append(row)

        return geo_coords, locations

    def extract(self, local_filename):
        """
        Function loads the already extracted GeoNames cities file or downloads and extracts it if
        it doesn't exist locally
        Args:
        local_filename (str): Path to local RG_FILE
        """
        if os.path.exists(local_filename):
            if self.verbose:
                print('Loading formatted geocoded file ...')
            rows = csv.DictReader(open(local_filename, 'rt'))
        else:
            rows = self.do_extract(GN_CITIES1000, local_filename)

        # Load all the coordinates and locations
        geo_coords, locations = [], []
        for row in rows:
            geo_coords.append((row['lat'], row['lon']))
            locations.append(row)
        return geo_coords, locations

    def do_extract(self, geoname_file, local_filename):
        gn_cities_url = GN_URL + geoname_file + '.zip'
        gn_admin1_url = GN_URL + GN_ADMIN1
        gn_admin2_url = GN_URL + GN_ADMIN2

        cities_zipfilename = geoname_file + '.zip'
        cities_filename = geoname_file + '.txt'

        if not os.path.exists(cities_zipfilename):
            if self.verbose:
                print('Downloading files from Geoname...')

            import urllib.request
            urllib.request.urlretrieve(gn_cities_url, cities_zipfilename)
            urllib.request.urlretrieve(gn_admin1_url, GN_ADMIN1)
            urllib.request.urlretrieve(gn_admin2_url, GN_ADMIN2)

        if self.verbose:
            print('Extracting %s...' % geoname_file)
        _z = zipfile.ZipFile(open(cities_zipfilename, 'rb'))
        open(cities_filename, 'wb').write(_z.read(cities_filename))

        if self.verbose:
            print('Loading admin1 codes...')
        admin1_map = {}
        t_rows = csv.reader(open(GN_ADMIN1, 'rt'), delimiter='\t')
        for row in t_rows:
            admin1_map[row[ADMIN_COLUMNS['concatCodes']]] = row[ADMIN_COLUMNS['asciiName']]

        if self.verbose:
            print('Loading admin2 codes...')
        admin2_map = {}
        for row in csv.reader(open(GN_ADMIN2, 'rt'), delimiter='\t'):
            admin2_map[row[ADMIN_COLUMNS['concatCodes']]] = row[ADMIN_COLUMNS['asciiName']]

        if self.verbose:
            print('Creating formatted geocoded file...')
        writer = csv.DictWriter(open(local_filename, 'wt'), fieldnames=RG_COLUMNS)
        rows = []
        for row in csv.reader(open(cities_filename, 'rt'), delimiter='\t', quoting=csv.QUOTE_NONE):
            lat = row[GN_COLUMNS['latitude']]
            lon = row[GN_COLUMNS['longitude']]
            name = row[GN_COLUMNS['asciiName']]
            cc = row[GN_COLUMNS['countryCode']]

            admin1_c = row[GN_COLUMNS['admin1Code']]
            admin2_c = row[GN_COLUMNS['admin2Code']]

            cc_admin1 = cc+'.'+admin1_c
            cc_admin2 = cc+'.'+admin1_c+'.'+admin2_c

            admin1 = ''
            admin2 = ''

            if cc_admin1 in admin1_map:
                admin1 = admin1_map[cc_admin1]
            if cc_admin2 in admin2_map:
                admin2 = admin2_map[cc_admin2]

            write_row = {
                'lat': lat,
                'lon': lon,
                'name': name,
                'admin1': admin1,
                'admin2': admin2,
                'cc': cc}
            rows.append(write_row)
        writer.writeheader()
        writer.writerows(rows)

        if self.verbose:
            print('Removing extracted %s to save space...' % geoname_file)
        os.remove(cities_filename)

        return rows


@singleton
class RGeocoder(RGeocoderImpl):
    pass


def geodetic_in_ecef(geo_coords):
    geo_coords = np.asarray(geo_coords).astype(np.float)
    lat = geo_coords[:, 0]
    lon = geo_coords[:, 1]

    lat_r = np.radians(lat)
    lon_r = np.radians(lon)
    normal = A / (np.sqrt(1 - E2 * (np.sin(lat_r) ** 2)))

    x = normal * np.cos(lat_r) * np.cos(lon_r)
    y = normal * np.cos(lat_r) * np.sin(lon_r)
    z = normal * (1 - E2) * np.sin(lat)

    return np.column_stack([x, y, z])


def rel_path(filename):
    """
    Function that gets relative path to the filename
    """
    return os.path.join(os.getcwd(), os.path.dirname(__file__), filename)


def get(geo_coord, mode=2, verbose=True):
    """
    Function to query for a single coordinate
    """
    if not isinstance(geo_coord, tuple) or not isinstance(geo_coord[0], float):
        raise TypeError('Expecting a tuple')

    _rg = RGeocoder(mode=mode, verbose=verbose)
    return _rg.query([geo_coord])[0]


def search(geo_coords, mode=2, verbose=True):
    """
    Function to query for a list of coordinates
    """
    if not isinstance(geo_coords, tuple) and not isinstance(geo_coords, list):
        raise TypeError('Expecting a tuple or a tuple/list of tuples')
    elif not isinstance(geo_coords[0], tuple):
        geo_coords = [geo_coords]

    _rg = RGeocoder(mode=mode, verbose=verbose)
    return _rg.query(geo_coords)


if __name__ == '__main__':
    print('Testing single coordinate through get...')
    city = (37.78674, -122.39222)
    print('Reverse geocoding 1 city...')
    result = get(city)
    print(result)

    print('Testing coordinates...')
    cities = [(41.852968, -87.725730), (48.836364, 2.357422)]
    print('Reverse geocoding %d locations ...' % len(cities))
    results = search(cities)
    print(results)
