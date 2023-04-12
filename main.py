import json
import os
import shutil
from os import mkdir, makedirs, stat
from os.path import exists, join

import demjson3
import requests
from bs4 import BeautifulSoup

from coordinate import update_delta_and_total, expand_coordinate
from models.country import Country
from models.park import Park

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/112.0.0.0 Safari/537.36 ',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.7',
    'accept-encoding': 'gzip, deflate, br',
    'cookie': 'cookiesDisclosureCount=1; __utma=61341485.1061748106.1681119771.1681119771.1681119771.1; '
              '__utmc=61341485; __utmz=61341485.1681119771.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); '
              '__utmt=1; __utmb=61341485.1.10.1681119771',
}
base_dir = 'parks'
country_list_file_name = 'country.json'
park_list_file_name = 'park_run_event.json'
park_config_file_name = 'config.json'
park_course_html_file_name = 'course.html'
google_page_data_file_name = 'google.pageData.json'
coordinate_file_name = 'google.coordinate.json'
coordinate_raw_file_name = 'google.coordinate.raw.json'


def get_country_list():
    file = open(country_list_file_name, 'r')
    json_string = file.read()
    json_array = json.loads(json_string)
    _list = []
    for item in json_array:
        _list.append(Country(item['name_en'], item['name_cn'], item['id'], item['code']))
    return _list


def country_list_to_dict(country_list):
    _dict = {}
    for country in country_list:
        _dict[country.id] = country
    return _dict


def get_park_list():
    park_list = []

    file = open(park_list_file_name, 'r')
    json_string = file.read()
    obj = json.loads(json_string)

    _countries = obj['countries']
    _country_map = country_list_to_dict(get_country_list())
    # country_codes = countries.keys()
    # for country_code in country_codes:
    #     print(f'{country_code}\'s url: {countries[country_code]["url"]}')

    parks = obj['events']['features']
    for park in parks:
        _props = park["properties"]
        _park_code = _props["eventname"]
        _country_id = str(_props["countrycode"])
        _course_url = f'https://{_countries[_country_id]["url"]}/{_park_code}/course'
        _park_obj = Park({"code": _park_code, "country_code": _country_map[_country_id].code, "course_url": _course_url})
        park_list.append(_park_obj)

    return park_list


def get_google_map_address(park_dir, park):
    _config_file_path = join(park_dir, park_config_file_name)
    if exists(_config_file_path):
        _config_file = open(_config_file_path)
        _read_park = json.load(_config_file, object_hook=Park)
        _google_map_url = _read_park.google_map_url
        _config_file.close()
        return _google_map_url

    resp = requests.get(park.course_url, headers=headers)
    html_doc = resp.text  # text 屬性就是 html 檔案
    soup = BeautifulSoup(html_doc, "html.parser")  # 指定 "html.parser" 作為解析器
    # print(soup.prettify())  # 把排版後的 html 印出來

    html_file = open(join(park_dir, park_course_html_file_name), 'w')
    html_file.write(soup.prettify())
    html_file.close()

    iframe_node = soup.find("iframe")
    google_map_address = iframe_node.get("src")

    _config_file = open(_config_file_path, 'w')
    park.google_map_url = google_map_address
    _config_file.write(json.dumps(park.__dict__))
    _config_file.close()

    return google_map_address


def get_google_route_coordinates(url):
    resp = requests.get(url, headers=headers)
    html_doc = resp.text  # text 屬性就是 html 檔案
    soup = BeautifulSoup(html_doc, "html.parser")  # 指定 "html.parser" 作為解析器
    # print(soup.prettify())  # 把排版後的 html 印出來
    script_array = soup.find_all("script")
    target_json = ''
    for script in script_array:
        text = str(script.getText())
        flag_start = '_pageData = '
        pos = text.find(flag_start)
        if pos != -1:
            target_json = text.partition(flag_start)[2]
            flag_end = ';'
            target_json = target_json.rstrip(flag_end)
            break
    return target_json


def find_coordinate_list(target):
    target_type = str(type(target))
    if target_type.find('list') != -1:
        item_count = len(target)
        if item_count == 2 and str(type(target[0])).find('float') != -1:
            return [target]
        else:
            _coordinates = []
            for idx in range(item_count):
                res = find_coordinate_list(target[idx])
                if len(res) != 0:
                    _coordinates = _coordinates + res
            return _coordinates
    else:
        return []


def find_coordinate_values(obj):
    obj_type = str(type(obj[0]))
    if obj_type.find('float') != -1:
        lat = obj[0]
        lng = obj[1]
        return [{"lng": lng, "lat": lat}]
    elif obj_type.find('list') != -1:
        points = []
        for item in obj:
            points = points + find_coordinate_values(item)
        return points
    else:
        return []


def transform_coordinate_to_obj_array(raw_array):
    obj_array = []
    for item0 in raw_array:
        obj_array = obj_array + find_coordinate_values(item0)
    return obj_array


def transform_latlng_to_lnglat(raw_array):
    obj_array = []
    for point in raw_array:
        lat = point[0][0]
        lng = point[0][1]
        obj_array.append([lng, lat])
    return obj_array


def repack_and_save_data(park_dir, json_array):
    arr1 = json_array[1][6]
    coordinate_array = []
    stop = 0
    for idx3 in range(len(arr1)):
        arr0 = arr1[idx3][12][0][13][0]
        for idx1 in range(len(arr0)):
            for idx2 in range(1, 4):
                coordinate_array = find_coordinate_list(arr0[idx1][idx2])
                if len(coordinate_array) != 0:
                    stop = 1
                    break
            if stop == 1:
                break
        if stop == 1:
            break

    # uncomment follow 2 lines if you want to copy the lnglat to mapbox
    # lnglat_array = transform_latlng_to_lnglat(coordinate_array)
    # print(json.dumps(lnglat_array))

    lnglat_object_array = transform_coordinate_to_obj_array(coordinate_array)

    if len(coordinate_array) != 0:

        lnglat_object_array[0]['delta'] = 0
        lnglat_object_array[0]['distance'] = 0
        update_delta_and_total(lnglat_object_array)

        total = lnglat_object_array[len(lnglat_object_array) - 1]['distance']
    else:
        total = 0

    export_json = json.dumps(lnglat_object_array)
    # print(export_json)

    output = open(join(park_dir, coordinate_file_name), 'w')
    output.write(export_json)
    output.close()

    return total


def get_park_coordinate(park):
    _park_dir = join(base_dir, park.country_code, park.code)
    if not exists(_park_dir):
        makedirs(_park_dir)

    _coordinate_file_path = join(_park_dir, coordinate_file_name)
    if exists(_coordinate_file_path) and stat(_coordinate_file_path).st_size > 0:
        return False

    _google_page_data_file_path = join(_park_dir, google_page_data_file_name)
    if not exists(_google_page_data_file_path):

        _google_map_url = get_google_map_address(_park_dir, park)
        # print(_google_map_url)

        _encoded_json = get_google_route_coordinates(_google_map_url)
        _decoded_json = demjson3.decode(_encoded_json)

        _google_file = open(_coordinate_file_path, 'w')
        _google_file.write(_decoded_json)
        _google_file.close()
    else:
        _google_file = open(_google_page_data_file_path, 'r')
        _decoded_json = _google_file.read()
        _google_file.close()

    repack_and_save_data(_park_dir, json.loads(_decoded_json))

    return True


def expand_park_coordinate(park):
    _park_dir = join(base_dir, park.country_code, park.code)
    _coordinate_file_path = join(_park_dir, coordinate_file_name)
    if not exists(_coordinate_file_path):
        return False

    _raw_file = open(_coordinate_file_path, 'r')
    _json_string = _raw_file.read()
    _raw_file.close()
    if _json_string == '':
        return False
    _raw_coordinate = json.loads(_json_string)

    # 扩充后的数组
    _has_expanded = False
    _expand_array = expand_coordinate(_raw_coordinate)
    if len(_expand_array) != len(_raw_coordinate):
        # 备份旧文件
        shutil.copy2(_coordinate_file_path, join(_park_dir, coordinate_raw_file_name))
        # 用w+模式,从头写入,相当于覆盖原文件
        _new_file = open(_coordinate_file_path, 'w')
        _new_file.write(json.dumps(_expand_array))
        _new_file.close()
        _has_expanded = True
    return _has_expanded


def clear_old_files(park):
    _park_dir = join(base_dir, park.country_code, park.code)
    # if exists(_park_dir):
    #     shutil.rmtree(_park_dir)

    _coordinate_file_path = join(_park_dir, coordinate_file_name)
    if exists(_coordinate_file_path):
        os.remove(_coordinate_file_path)

    _coordinate_raw_file_path = join(_park_dir, coordinate_raw_file_name)
    if exists(_coordinate_raw_file_path):
        os.remove(_coordinate_raw_file_path)


def deal_parks(park_list, force=False):
    park_size = len(park_list)
    for idx in range(len(park_list)):
        _park = park_list[idx]
        if force:
            clear_old_files(_park)
        try:
            _downloaded = get_park_coordinate(_park)
            if _downloaded:
                print(f'[{idx + 1}/{park_size}]route {_park.code} completed.')
            _expanded = expand_park_coordinate(_park)
            if _expanded:
                print(f'[{idx + 1}/{park_size}]route {_park.code} expand completed.')
        except Exception as ex:
            print(f'[{idx}/{park_size}]route {_park.code} has ERROR: {ex}')


if __name__ == '__main__':
    if not exists(base_dir):
        mkdir(base_dir)
    # _park_dict = {'bairnsdale': 'https://www.parkrun.com.au/bairnsdale/course'}
    _park_list = get_park_list()
    # deal_parks(_park_list)

    _some_codes = ['rezerwatstrzelnica', 'aggeneys', 'wotton',
                   'coppertrail', 'gayndahriverwalk', 'theoldrailtrail-juniors', 'thegrandcanalway', ]
    _some = []
    for _p in _park_list:
        if _p.code in _some_codes:
            _some.append(_p)
    deal_parks(_some, force=True)

    # pa = {'lng': 113.31474304199219, 'lat': 23.04990577697754, 'delta': 0, 'distance': 0}
    # pb = {'lng': 113.3223648071289, 'lat': 23.049406051635742, 'delta': 0, 'distance': 0}
    # pb['distance'] = pb['delta'] = geodistance(pa, pb)
    # result = expand_coordinate([pa, pb])
    # print(json.dumps(transform_to_mapbox(result)))
