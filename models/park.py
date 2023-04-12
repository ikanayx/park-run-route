class Park:
    code: ''
    country_code: ''
    course_url: ''
    google_map_url: ''

    def __init__(self, _dict):
        self.__dict__.update(_dict)
