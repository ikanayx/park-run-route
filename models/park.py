class Park:
    code: ''
    country_code: ''
    course_url: ''
    route_length_describe_in_coures: 0
    google_map_url: ''
    google_coordinate_meter: 0

    def __init__(self, code, country_code, course_url, route_meters):
        self.code = code
        self.country_code = country_code
        self.course_url = course_url
        self.route_meters = route_meters
