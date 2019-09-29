import random

import numpy as np
import pandas as pd

import rvgeocoder as rvg
from pyspark.sql.functions import PandasUDFType, col, pandas_udf
from pyspark.sql.session import SparkSession

## TODO: put your custom geocoding files here
files = []

# if we are doing this here mode must be equal to 1 as mode=2 does not work when trying to serialize 
# as ckDTree has some issues with serialization
# files_stream = rvg.RGeocoderDataLoader.load_files_stream(files)
# rgeo = rvg.RGeocoder(mode=1, stream=files_stream)

# return list of strings and not tuple as pandas_udf does not support structs/maps at the moment
def reverse(slat, slon):
    coords = list(zip(slat.values, slon.values))
    if files:
        files_stream = rvg.RGeocoderDataLoader.load_files_stream(files)
        rgeo = rvg.RGeocoder(stream=files_stream)
    else:
        rgeo = rvg.RGeocoder()

    res = rgeo.query(coords)
    
    pdf = pd.DataFrame()
    pdf['locs'] = [[x['cc'], x['name']] for x in res]
    return pdf.locs


def gen_coords_list(n):
    return [(round(random.uniform(-90,90),2), round(random.uniform(-180,180),2)) for i in range(n)]


def main():
    # create spark session
    spark_packages = 'com.amazonaws:aws-java-sdk-pom:1.10.34,org.apache.hadoop:hadoop-aws:2.7.7'
    spark = SparkSession.builder.appName('test_app') \
        .config('spark.jars.packages', spark_packages) \
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", 2) \
        .config("spark.sql.session.timeZone", "UTC") \
        .config("spark.sql.execution.arrow.enabled", "true") \
        .config("spark.sql.execution.arrow.fallback.enabled", "true") \
        .config("spark.sql.execution.arrow.enabled", "true") \
        .getOrCreate()

    # create sample DF, can load from files / streams etc
    sample_size = 10000
    coords = gen_coords_list(sample_size)
    df = spark.createDataFrame(coords, ['latitude', 'longitude'])

    ##################################################################################################
    ##################################################################################################
    ##################################################################################################
    #
    #  THIS IS THE INTERESTING PART - ALL THE REST IS JUST SETUP AND USAGE CODE FOR EXAMPLE
    #
    # run our reverse code that returns a list of country, name (can add also admin1 etc if wanted)
    reverse_udf = pandas_udf(reverse, 'array<string>', PandasUDFType.SCALAR)
    df = df.withColumn('place_names', reverse_udf(df.latitude, df.longitude))
    df = df.select('latitude', 'longitude', col('place_names')[1].alias('name'), col('place_names')[0].alias('cc'))
    #
    #
    ##################################################################################################
    ##################################################################################################
    ##################################################################################################
    
    # Example of usange - print num of coords in US
    places_in_us = df.filter(col('cc') == 'US').count()
    print('Found %s/%s places in US' % (places_in_us, sample_size))


def main_pandas_debug():
    pdf = pd.DataFrame(np.random.randint(0,90,size=(100, 2)), columns=['lat', 'lon'])    
    print(reverse(pdf.lat, pdf.lon))


if __name__ == "__main__":
    main()
