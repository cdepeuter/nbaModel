from bs4 import BeautifulSoup
import collections
import pprint as pp
import urllib2
import settings
import datetime as dt
import json

def getAllIds():
	#if there are no games we'll need to get the teams from the web
	teamUrl = "http://www.si.com/nba/teams"
	page=urllib2.urlopen(teamUrl)
	soup = BeautifulSoup(page.read())
	teams = [item["href"].replace("/nba/team/", "") for item in soup.find_all("a") if "href" in item.attrs and "/nba/team/" in item["href"]]


	#grab all games for teams
	allIds = []
	for team in teams:
	    url =  "http://www.si.com/nba/team/"+team+"/schedule?season="+str(year)
	    page=urllib2.urlopen(url)
	    soup = BeautifulSoup(page.read())
	    ids = [item["data-id"] for item in soup.find_all("tr", class_="component-scoreboard-list final") if "data-id" in item.attrs]
	    allIds += ids
	    print(team, len(ids))

	print(len(allIds))
	allIds = list(set(allIds))
	print(len(allIds))
	return allIds

def getIdsFromDate(year, month, day):
	d = dt.datetime(year, month, day)
	allIds = []
	td = dt.timedelta(days=3)
	for i in range(0, 50):
	    url = "http://www.si.com/nba/schedule?date="
	    url = url + d.strftime("%Y-%m-%d")
	    page=urllib2.urlopen(url)
	    soup = BeautifulSoup(page.read())
	    print(url)
	    ids = [item["data-id"] for item in soup.find_all("tr", class_="component-scoreboard-list final") if "data-id" in item.attrs]
	    allIds += ids
	    allIds = list(set(allIds))
	    print(len(allIds))
	    d = d + td
	   
	return allIds

def buildEventTree():
	allEvents = {}
	allEventDetails = collections.defaultdict(set)
	for i in allIds:
	    f = "games/"+str(i)+".json"
	    with open(f) as infile:
	        data = json.load(infile)
	        pbp = data['apiResults'][0]['league']['season']['eventType'][0]['events'][0]['pbp']
	        events = [play['playEvent'] for play in pbp if 'name' in play['playEvent']]
	        eventsD = {play['name']: play['playEventId'] for play in events  }
	        tups = [(play["playEventId"], (play["playDetail"]['playDetailId'], play['playDetail']['name'])) for play in events if 'name' in play['playDetail']] 
	        for tup in tups:
	            allEventDetails[tup[0]].add(tup[1])
	            
	        allEvents = dict(allEvents, **eventsD)
	   
	pp.pprint(allEvents)

	return False

def scrapeGameJSON(id):
	 url = "http://www.si.com/pbp/liveupdate?json=1&sport=basketball%2Fnba&id="+str(id)+"&box=true&pbp=true&linescore=true"
    print(url)
    data = json.loads(urllib2.urlopen(url).read())
    #print(data['apiResults'])
    seasonType = data['apiResults'][0]['league']['season']['eventType'][0]['name']
    print(seasonType)
    seasonConvert = {"Preseason": "pre.", "Regular Season": "reg."}
    filename = "games/"+year+"/"+seasonConvert[seasonType]+str(id)+".json"
    print(filename)
    f = open(filename, 'w')
    json.dump(data, f)

if __name__ == "__main__":
	global year
	year = settings.year
	ids = getAllIds()
	for i in ids:
		scrapeGameJSON(id)
	   

