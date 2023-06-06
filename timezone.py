from timezonefinder import TimezoneFinder

if __name__ == '__main__':
    tf = TimezoneFinder()  # reuse
    query_points = [(13.358, 52.5061)]
    for lng, lat in query_points:
        tz = tf.timezone_at(lng=lng, lat=lat)  # 'Europe/Berlin'
        print(tz)

