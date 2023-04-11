import json
from os import mkdir, makedirs
from os.path import exists, join

import demjson3
import requests
from bs4 import BeautifulSoup

from coordinate import update_delta_and_total
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


def get_country_list():
    file = open('country.json', 'r')
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

    file = open('park_run_event.json', 'r')
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
        _park_obj = Park(_park_code, _country_map[_country_id].code, _course_url, 0)
        park_list.append(_park_obj)

    return park_list


def get_google_map_address(country_code, park_code, url):
    resp = requests.get(url, headers=headers)
    html_doc = resp.text  # text 屬性就是 html 檔案
    soup = BeautifulSoup(html_doc, "html.parser")  # 指定 "html.parser" 作為解析器
    # print(soup.prettify())  # 把排版後的 html 印出來

    html_file = open(f'{base_dir}/{country_code}/{park_code}/course.html', 'w')
    html_file.write(soup.prettify())
    html_file.close()

    iframe_node = soup.find("iframe")
    google_map_address = iframe_node.get("src")
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
        if item_count > 3:
            return target
        else:
            for idx in range(item_count):
                res = find_coordinate_list(target[idx])
                if len(res) != 0:
                    return res
            return []
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


def repack_and_save_data(park_code, park_dir, json_array):
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

    output = open(f'{park_dir}/google.coordinate.json', 'w')
    output.write(export_json)
    output.close()

    return total


def get_park_coordinate(park):
    _park_dir = join(base_dir, park.country_code, park.code)
    if not exists(_park_dir):
        makedirs(_park_dir)

    _coordinate_file_path = join(_park_dir, 'google.pageData.json')
    if exists(_coordinate_file_path):
        return

    _google_map_url = ''
    _config_file_path = join(_park_dir, 'config.json')
    if exists(_config_file_path):
        _config_file = open(_config_file_path)
        _read_park = json.load(_config_file, object_hook=Park)
        _google_map_url = _read_park.google_map_url
        _config_file.close()

    if _google_map_url == '':
        _google_map_url = get_google_map_address(park.country_code, park.code, park.course_url)
        park.google_map_url = _google_map_url

    # print(_google_map_url)
    _encoded_json = get_google_route_coordinates(_google_map_url)
    _decoded_json = demjson3.decode(_encoded_json)

    _google_file = open(_coordinate_file_path, 'w')
    _google_file.write(_decoded_json)
    _google_file.close()

    meters = repack_and_save_data(park.code, _park_dir, json.loads(_decoded_json))
    park.google_coordinate_meter = round(meters, 2)

    _config_file = open(_config_file_path, 'w')
    _config_file.write(json.dumps(park.__dict__))
    _config_file.close()


def get_parks_coordinate(park_list):
    park_size = len(park_list)
    for idx in range(len(park_list)):
        _park = park_list[idx]
        try:
            get_park_coordinate(_park)
            print(f'[{idx}/{park_size}]route {_park.code} completed.')
            # in case of google and parkrun website detected and block the program.
            # time.sleep(1)
        except Exception as ex:
            print(f'[{idx}/{park_size}]route {_park.code} has ERROR: {ex}')


if __name__ == '__main__':
    if not exists(base_dir):
        mkdir(base_dir)
    # _park_dict = {'bairnsdale': 'https://www.parkrun.com.au/bairnsdale/course'}
    _park_list = get_park_list()
    get_parks_coordinate(_park_list)
