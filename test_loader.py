import csv
import rvgeocoder as rvg
import random
import time

def gen_test_file(n=1000, filename='coordinates_1000.csv'):
    with open('test/%s' % filename, 'w') as f:
        for _ in range(n):
            lat = round(random.uniform(-90,90),2)
            lon = round(random.uniform(-180,180),2)
            f.write('%s\t%s\n' % (lat, lon))

if __name__ == '__main__':
    cities = [(row[0],row[1]) for row in csv.reader(open('test/coordinates_1000000.csv','rt'),delimiter='\t')]
    
    rgeo = rvg.RGeocoderImpl.from_files(['test/file1.csv', 'test/file2.csv'])
    
    start = time.time()
    res = rgeo.query(cities)
    run_time = round(time.time() - start, 2)

    # print first 10 results
    import pprint
    pprint.pprint(res[:10])

    print('** run time is %s' % run_time)
