import datetime as dt


def year(request):
    d = dt.datetime.today()
    year1 = d.year

    return {'year': year1}
