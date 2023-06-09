from geographiclib.geodesic import Geodesic
from math import radians, cos, sin, asin, sqrt, ceil, floor
from os import listdir, mkdir, path
from os.path import isfile, isdir, join
import json


def expand_coordinate(coordinate_array):
    if len(coordinate_array) == 0:
        return coordinate_array
    # 扩充后的数组
    expansion_array = [coordinate_array[0]]
    for idx in range(1, len(coordinate_array)):
        prev = coordinate_array[idx - 1]
        curr = coordinate_array[idx]
        if curr['delta'] > 1:
            center_points = get_center_point(prev, curr, curr['delta'])
            if len(center_points) > 0:
                expansion_array = expansion_array + center_points
        expansion_array.append(curr)

    update_delta_and_total(expansion_array)
    return expansion_array


def geodistance(point1, point2, unit='m'):
    # 经纬度转换成弧度
    lng1, lat1, lng2, lat2 = map(radians, [float(point1['lng']), float(point1['lat']),
                                           float(point2['lng']), float(point2['lat'])])
    dlon = lng2 - lng1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    distance = 2 * asin(sqrt(a)) * 6371 * 1000  # 地球平均半径，6371km
    if unit == 'km':
        distance = round(distance / 1000, 3)
    else:
        distance = round(distance, 2)  # 单位用米，保留2位小数
    return distance


def get_center_point(point1, point2, distance):
    if distance < 1:
        # 两点距离小于1m，不执行点扩充
        return []

    # Define the ellipsoid
    geod = Geodesic.WGS84

    # Solve the Inverse problem
    inv = geod.Inverse(point1['lat'], point1['lng'], point2['lat'], point2['lng'])
    # 获得方位角
    azi1 = inv['azi1']
    # print('Initial Azimuth from point1 to point2 = ' + str(azi1))

    new_array = []
    step = 1  # 扩充点的距离：1m
    move = 0  # 移动的距离
    while move < distance - 1:
        move = move + step
        direct = geod.Direct(point1['lat'], point1['lng'], azi1, move)
        new_array.append({"lng": float(direct['lon2']),
                          "lat": float(direct['lat2']),
                          "delta": step,
                          "distance": point1['distance'] + move})
    return new_array


def transform_to_mapbox(raw_array):
    obj_array = []
    for point in raw_array:
        lat = point['lat']
        lng = point['lng']
        obj_array.append([lng, lat])
    return obj_array


def update_delta_and_total(coordinate_array):
    total = 0
    for index in range(1, len(coordinate_array)):
        curr = coordinate_array[index]
        prev = coordinate_array[index - 1]
        meters = geodistance(prev, curr)
        total += meters
        curr['delta'] = meters
        curr['distance'] = total

