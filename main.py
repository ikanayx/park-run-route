import requests
import json
import demjson3
import os
import time
from coordinate import update_delta_and_total
from bs4 import BeautifulSoup

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
output_dir = "output"


def get_park_coordinate():
    park_dict = get_all_country_course_index()
    park_size = len(park_dict.keys())
    idx = 0
    for park_code in park_dict.keys():
        idx = idx + 1
        if file_exists_check(park_code):
            # print(f'[{idx}/{park_size}]route {park_code} exists.')
            continue
        try:  # 使用 try，測試內容是否正確
            google_map_addr = get_google_map_address(park_dict[park_code])
            # print(google_map_addr)

            encoded_json = get_google_route_coordinates(google_map_addr)
            decoded_json = demjson3.decode(encoded_json)

            json_array = json.loads(decoded_json)
            total = repack_and_save_data(park_code, json_array)

            print(f'[{idx}/{park_size}]route {park_code} found {total} meter coordinates.')
            # in case of google and parkrun website detected and block the program.
            # time.sleep(1)
        except Exception as ex:
            print(f'[{idx}/{park_size}]route {park_code} has ERROR: {ex}')


def get_all_country_course_index():
    park_dict = {}

    file = open('park_run_event.json', 'r')
    json_string = file.read()
    obj = json.loads(json_string)
    # print(json.dumps(events['countries']['3']['url']))

    countries = obj['countries']
    # country_codes = countries.keys()
    # for country_code in country_codes:
    #     print(f'{country_code}\'s url: {countries[country_code]["url"]}')

    parks = obj['events']['features']
    for park in parks:
        props = park["properties"]
        park_code = props["eventname"]
        country_code = str(props["countrycode"])
        country_index = countries[country_code]["url"]
        course_url = f'https://{country_index}/{park_code}/course'
        # print(f'CoursePageUrl is {course_url}')
        park_dict[park_code] = course_url

    return park_dict


def get_google_map_address(url):
    resp = requests.get(url, headers=headers)
    html_doc = resp.text  # text 屬性就是 html 檔案
    soup = BeautifulSoup(html_doc, "html.parser")  # 指定 "html.parser" 作為解析器
    # print(soup.prettify())  # 把排版後的 html 印出來
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


def transform_coordinate_to_obj_array(raw_array):
    obj_array = []
    for item0 in raw_array:
        obj_array = obj_array + find_coordinate_values(item0)
    return obj_array


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


def transform_latlng_to_lnglat(raw_array):
    obj_array = []
    for point in raw_array:
        lat = point[0][0]
        lng = point[0][1]
        obj_array.append([lng, lat])
    return obj_array


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


def repack_and_save_data(park_code, json_array):
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

    output = open(f'{output_dir}/{park_code}.json', 'w')
    output.write(export_json)
    output.close()

    return total


def file_exists_check(park_code):
    return os.path.exists(f'{output_dir}/{park_code}.json')


if __name__ == '__main__':
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    get_park_coordinate()
