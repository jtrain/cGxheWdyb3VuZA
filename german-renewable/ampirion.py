import datetime
import urllib2
import StringIO
from xml.etree.ElementTree import ElementTree
import os
import StringIO
import shutil
import time

from pandas import DataFrame
from pandas.stats.moments import rolling_max
from matplotlib import pyplot

def cache(fn):
	"""
	Cache the fn so that we don't continually hit the amprion website.
	"""
	cache_loc = '.cache_html'
	try:
		os.mkdir(cache_loc)
	except OSError:
		pass

	def cached(date):
		cached_fname = os.path.join(cache_loc, date.strftime('%d-%m-%Y.html'))
		try:
			return open(cached_fname)
		except IOError:
			html = fn(date)
			time.sleep(0.5)

			with open(cached_fname, 'wb') as cachefile:
				shutil.copyfileobj(html, cachefile)

			return open(cached_fname)

	return cached

@cache
def html_for_day(date):
	"""
	Returns the PV production for the requested day in HTML format from the ampiron website.
	"""
	url = r'http://amprion.de/applications/applicationfiles/PV_einspeisung.php?mode=show&day={day}'
	return urllib2.urlopen(url.format(day=date.strftime('%d.%m.%Y')))

def handle_illformed_xml(fp):
	"""
	The ampiron website returns ill-formed xml that needs
	to be fixed before Python can read it.
	"""
	contents = fp.read().replace('"t', '" t')
	return StringIO.StringIO(contents)

def todate(datestr, timestr):
	"""
	returns a datetime object given a date string and time string.

	datestr: a date string in format DD.MM.YYYY
	timestr: a time string in format HH:MM - HH:MM

	the first period in the timestr interval is used for the time.
	"""
	date = datetime.datetime.strptime(datestr, '%d.%m.%Y')
	time = datetime.datetime.strptime(timestr[:5], '%H:%M')
	return date.replace(hour=time.hour, minute=time.minute)

def item_to_tuple(item):
	"""
	returns a tuple of:

	 (datetime, expost)

	from the `item` xml element.
	"""
	date = item.get('date')
	time = item.get('time')
	expost = item.get('expost')

	return (todate(date, time), float(expost))

# start of this month.
current_date = start_date = datetime.date(2010, 7, 1)
day = datetime.timedelta(days=1)
end_date = datetime.date.today()

pv_data = []

for i in range((end_date - start_date).days):
	try:
		html = html_for_day(current_date)
	except urllib2.URLError, e:
		continue
	finally:
		current_date = current_date + day

	tree = ElementTree()
	tree.parse(handle_illformed_xml(html))
	items = tree.iterfind('item')
	pv_data.extend(map(item_to_tuple, items))


pv = DataFrame.from_records(pv_data, index='timestamp', columns=["timestamp", "expost"])
fig = pyplot.figure()
rolling_max(pv, 4*24*30).plot(rot=15)
pyplot.title("Solar Photovoltaic production in Amprion's network Germany")
pyplot.ylabel("Rolling month maximum power produced [MW]")
pyplot.xlabel("Date")
pyplot.grid()
pyplot.savefig('ampiron.png')
