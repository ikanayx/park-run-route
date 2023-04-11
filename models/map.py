class Lnglat:
    lng = 0.0
    lat = 0.0
    delta = 0
    distance = 0

    def __init__(self, lng, lat, delta=0, distance=0):
        self.lng = lng
        self.lat = lat
        self.delta = delta
        self.distance = distance
