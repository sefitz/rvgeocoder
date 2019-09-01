# RvGeocoder
A Python library for offline reverse geocoding. It improves on an existing library called [reverse_geocoder](https://pypi.org/project/reverse_geocoder/1.5.1/) developed by [Ajay Thampi](https://github.com/thampiman/reverse-geocoder).

The package has not been updated sinse 2016 and this is an effort of keeping it a "live" project.

Main improvements on first version of this forked package:

- support init non-singleton instance of RGeocoder to support different stream simultaneously (creating RGeocoderImpl class to support that)
- added the capability change the header columns when loading custom stream and loaded different schemas
- added query_dist to support returning distance in addtion to the reverse geocoding data itself
- added do_extract to trigger extraction for any Geonames file, e.g: 1000, 15000 etc
- removed win32 and python2 support. added utility function to load data from files/buffers

* The init commit of this project is based on thampiman/reverse-geocoder Latest commit on Sep 15, 2016 a81b4095bf2cb7ef84d2187fcbc8945d5d8922d0 - and forks from there.

## Features
1. Besides city/town and country code, this library also returns the nearest latitude and longitude and also administrative regions 1 and 2.
2. This library also uses a parallelised implementation of K-D trees which promises an improved performance especially for large inputs.

By default, the K-D tree is populated with cities that have a population > 1000. The source of the data is [GeoNames](http://download.geonames.org/export/dump/). You can also load a custom data source so long as it is a comma-separated file with header (like [rg_cities1000.csv](https://github.com/sefiit/rvgeocoder/blob/master/rvgeocoder/rg_cities1000.csv)), containing the following columns:

- `lat`: Latitude
- `lon`: Longitude
- `name`: Name of place
- `admin1`: Admin 1 region
- `admin2`: Admin 2 region
- `cc`: ISO 3166-1 alpha-2 country code

For usage instructions, see below.

## Installation
For first time installation,
```
$ pip install rvgeocoder
```

Or upgrade an existing installation using,
```
$ pip install --upgrade rvgeocoder
```

### Dependencies
1. scipy
2. numpy

### Release Notes
1. v1.0.1 (29-Aug-19) - First version

## Usage
The library supports two modes:

1. Mode 1: Single-threaded K-D Tree (similar to [reverse_geocode](https://pypi.python.org/pypi/reverse_geocode/1.0))
2. Mode 2: Multi-threaded K-D Tree (default)

```python
import rvgeocoder as rvg

coordinates = (41.852968, -87.725730), (48.836364, 2.357422)
print(rvg.search(coordinates))
```

The above code will output the following:
```
[OrderedDict([('lat', '41.84559'),
              ('lon', '-87.75394'),
              ('name', 'Cicero'),
              ('admin1', 'Illinois'),
              ('admin2', 'Cook County'),
              ('cc', 'US')]),
 OrderedDict([('lat', '48.85341'),
              ('lon', '2.3488'),
              ('name', 'Paris'),
              ('admin1', 'Ile-de-France'),
              ('admin2', 'Paris'),
              ('cc', 'FR')])]
```

To use a custom data source for geocoding, you can load the file in-memory and pass it to the library as follows:
```python
import io
import rvgeocoder as rvg

geo = rvg.RGeocoder(stream=io.StringIO(open('custom_source.csv', encoding='utf-8').read()))
coordinates = (51.5214588,-0.1729636),(9.936033, 76.259952),(37.38605,-122.08385)
results = geo.query(coordinates)
```

As mentioned above, the custom data source must be comma-separated with a header as [rg_cities1000.csv](https://github.com/thampiman/reverse-geocoder/blob/master/reverse_geocoder/rg_cities1000.csv).

## Acknowledgements
1. Major inspiration is from Richard Penman's [reverse_geocode](https://bitbucket.org/richardpenman/reverse_geocode) library 
2. First version based on [reverse_geocoder](https://pypi.org/project/reverse_geocoder/1.5.1/) developed by [Ajay Thampi](https://github.com/thampiman/reverse-geocoder)
3. Parallelised implementation of K-D Trees is extended from this [article](http://folk.uio.no/sturlamo/python/multiprocessing-tutorial.pdf) by [Sturla Molden](https://github.com/sturlamolden)
4. Geocoded data is from [GeoNames](http://download.geonames.org/export/dump/)

## License
Copyright (c) 2019 Sefi Itzkovich and contributors. This code is licensed under the LGPL License.
