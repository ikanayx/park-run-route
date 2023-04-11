class Country:
    name_cn: ''
    name_en: ''
    id: ''
    code: ''

    def __init__(self, name_en, name_cn, country_id, code):
        self.name_cn = name_cn
        self.name_en = name_en
        self.id = country_id
        self.code = code
