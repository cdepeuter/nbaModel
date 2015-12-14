import os
import json
import sys
import settings

year = settings.year
path = "games/"+year+"/"
files = [path+f for f in os.listdir(path) if ".json" in f]
#print(files)
global teams
teams = {}
for f in files:
    with open(f) as infile:
        data = json.load(infile)
        team1 = data['apiResults'][0]['league']['season']['eventType'][0]['events'][0]['teams'][0]
        team2 = data['apiResults'][0]['league']['season']['eventType'][0]['events'][0]['teams'][1]
        #teams.add(team1)
        teams[team1['teamId']] = {"loc":team1['location'], "abbrev" :team1['abbreviation'], "name":team1['nickname'], "id":team1['teamId']} 
        teams[team2['teamId']] = {"loc":team2['location'], "abbrev" :team2['abbreviation'], "name":team2['nickname'], "id":team2['teamId']} 
        
        #print(team1)
        if len(teams) == 30:
            break

def getTeamById(id):
    if id is not None and 0 < id <= 30 or id == 5312:
        return teams[id]
    return None


def getTeamByName(name):
    if name is not None:
        for i in teams:
            if teams[i]['name'] == name:
                return teams[i]
    return None

def getTeamByAbbrev(abbrev):
    if abbrev is not None:
        for i in teams:
            if teams[i]['abbrev'] == abbrev:
                return teams[i]
    return None

def getTeamByLoc(loc):
    if loc is not None:
        for i in teams:
            if teams[i][ 'loc'] == loc:
                return teams[i]
    return None

def getAllTeams():
	return teams
