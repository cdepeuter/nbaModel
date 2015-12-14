import requests
from StringIO import StringIO
import numpy as np
import pandas as pd 
import datetime as dt
import json
import pprint as pp
import collections
import os
import sys
import settings
from os import path

def getMeta(game):
    _meta = {}
    teams = game['teams']
    _meta['gameId'] = game['eventId']
    _meta['date'] = game['startDate'][0]['full']
    _meta['homeId'] = teams[0]['teamId'] if teams[0]['teamLocationType']['name'] == "home" else teams[1]['teamId']
    _meta['homeName'] = teams[0]['nickname'] if teams[0]['teamLocationType']['name'] == "home" else teams[1]['nickname']
    _meta['homeLoc'] = teams[0]['location'] if teams[0]['teamLocationType']['name'] == "home" else teams[1]['location']
    _meta['awayId'] = teams[1]['teamId'] if teams[1]['teamLocationType']['name'] == "away" else teams[0]['teamId']
    _meta['awayName'] = teams[1]['nickname'] if teams[1]['teamLocationType']['name'] == "away" else teams[0]['nickname']
    _meta['awayLoc'] = teams[1]['location'] if teams[1]['teamLocationType']['name'] == "away" else teams[0]['location']
    return _meta

def whichEndOfQtr(play, meta):
    if play['playEvent']['playEventId'] == 15:
        return play['period']
    return -1

def getJumpWinner(play, sec, meta):
    #try to figure out from a jump ball play who won the jump
    #return 0 if home, 1 if away, -1 if inconclusive

    #some games just dont give clear jump winners in the pbp, just hack it
    homeTipWinners = [1459859, 1460262, 1460652, 1459491, 1459481, 1460363, 1459567, 1460093, 1460543, 1459752, 1460014, 1460332, 1460081, 1460014, 1577738, 1571495,1577641,1570488,1570538, 1571058]
    awayTipWinners = [1541218, 1460501, 1459628, 1459773,  1459839, 1460089, 1460517, 1459621, 1459530 ,1460272, 1460470, 1539625, 1459454, 1571054, 1570835, 1570849]
    
    #mid game jumps + playId
    homeOtherTipWinners = [(1460012, "236"), (1460312, "73"), (1459869, "71"), (1459784, "231"), (1460051, "158"), (1459725, "442"), (1460486, "27"), (1577627, "470"), (1570503, "257"), (1570843, "331")]
    awayOtherTipWinners = [(1460163, "486"), (1459854, "424"), (1460014, "30"), (1571206, "350")]
    
    if (meta["gameId"], play['playId']) in awayOtherTipWinners:
        return 1
    elif (meta["gameId"], play['playId']) in homeOtherTipWinners:
        return 0
    
    if play['period'] == 1:
        if meta["gameId"] in awayTipWinners:
            return 1
        elif meta['gameId'] in homeTipWinners:
            return 0

    allEventIds = set()
    allEventDetails = set()
         
    #hmm we cant decide , lets check all the plays this second for clues
    for p in sec:
        allEventIds.add(p['playEvent']['playEventId'])
        if 'playDetail' in p['playEvent'] and 'playDetailId' in p['playEvent']['playDetail']:  
            allEventDetails.add((p['playEvent']['playEventId'], p['playEvent']['playDetail']['playDetailId']))
    
    if 6 in allEventIds:
        #theres a dreb in this sec even if we can determine jumpwinner the poss is over on that event
        return -1
    
    #if theres 3 players in the play, the team with 2 players won the jump
    if len(play['players']) == 3:
        teamIds = [player['teamId'] for player in play['players']]
        return int(teamIds.count(meta['awayId']) > 1)

    
    if 5 in allEventIds:
        #orebound in this second
        if meta['onOffense'] == "home":
            return 0
        elif meta['onOffense'] == "away":
            return 1
    elif (9, 5) in allEventDetails or (8,3) in allEventDetails:
        #violation or foul, who done it?
        jbvp = None
        for p in sec:
            if 'playDetail' in p['playEvent'] and 'playDetailId' in p['playEvent']['playDetail']:
                if (p['playEvent']['playDetail']['playDetailId'] == 5 and p['playEvent']['playEventId'] == 9) or \
                    (p['playEvent']['playDetail']['playDetailId'] == 3 and p['playEvent']['playEventId'] == 8):
                    jbvp = p
                    break
        #print(jbvp['players'][0]['teamId'], meta['awayId'], meta['homeId'])
        return 0 if jbvp['players'][0]['teamId'] == meta['awayId'] else 1
    
    return -1
            

def isPossessionOver(play, sec, meta):
    '''play is the play json, sec is other plays that happened that second
        -possession is definitely over after turnover, end of qtr, defensive rebound
        -if its a made shot, need to make sure there wasnt a foul that possession, 
            otherwise he has to make the free throw for it to be over (wait until that play event)
        -if 2nd of 2 fts, or 3 of 3 its over
        -jump ball mid game team which had it could lose it, possession over 
        -all hacks explained in hacksExplained.txt
    '''

    
    hacksFalse = [(1459778, "372"), (1459753, "36"),  (1459954, "375"), (1459925, "320"), (1460173,"181"), (1459745, "329"), (1459973, "102"),\
            (1460184, "440"), (1459497, "345"), (1460216, "337"), (1459666, "249"), (1459666, "253"), (1460551, "369"), (1570542, "303"), (1570617, "16"), \
            (1570748, "66"), (1571124, "232"), (1571086, "365"), (1570839, "258"), (1570987, "337"), (1571694, "212"), (1571161, "388")]
    hackTrue = [(1459678 , "12"), (1460579, "352"), (1459493, "11"), (1460147, "151"), (1460413, "436"), (1459928, "516"), (1577618, "479"), (1570529, "17"),\
             (1570839, "260"), (1571103, "182"), (1570615, "442"), (1571476, "467"),(1571462, "473"),  (1570843, "331"),  (1571428, "516"),  (1571409, "15")]
    if (meta['gameId'], play['playId'] ) in hacksFalse:
        return False
    if (meta['gameId'], play['playId'] ) in hackTrue:
        return True


    allEventIds = set()
    allEventDetails = set()
    
    eid = play['playEvent']['playEventId']
    thisDetailId = 0 if 'playDetailId' not in play['playEvent']['playDetail'] else play['playEvent']['playDetail']['playDetailId']
    eop = [6,15,7,3]
    #batch the other events that happened this second, we might need to look at em
    if len(sec) > 1:
        for p in sec:   
            allEventIds.add(p['playEvent']['playEventId'])
            if 'playDetail' in p['playEvent'] and 'playDetailId' in p['playEvent']['playDetail']:
                allEventDetails.add((p['playEvent']['playEventId'], p['playEvent']['playDetail']['playDetailId']))

    #turnover, dreb, end of quarter, definitely over
    if eid in eop[:-1]:
        return True

    #made shot
    if eid == 3:
        #print("made shot", play['playText'], allEventDetails)
        #set([11, 8, 10, 3, 1]), set([(8, 1), (3, 42), (1, 11), (11, 2), (1, 12)]))
        if len(allEventIds.intersection([8,1,2])) == 0:
            #if there were any of these (foul or ft) we need to do some more thinking
            return True
        elif 8 in allEventIds and (1 not in allEventIds and 2 not in allEventIds):
            if (8,2) in allEventDetails or (8, 29) in allEventDetails:
                #shooting foul
                if (9,7) not in allEventDetails and (7,17) not in allEventDetails and (7,15) not in allEventDetails:
                    #violations, explained
                    raise ValueError("there was a shooting foul but no fts????")
                return False
            else:
                #reg foul might not mean free throws, (could happen on inbounds after)
                return True
        elif (8,2) in allEventDetails or (8, 29) in allEventDetails:
            #shooting foul, need to wait for the free throw event to see
            return False
        elif (8,6) in allEventDetails:
            #away from play foul. Check if its on the team who is currently on offense, if so, poss over
            foulPlay = findWhere(sec, (8,6))
            if debug:
                print("away from play foul", foulPlay['players'][0]['teamId'],  meta[meta['onOffense']+"Id"])
                pp.pprint(foulPlay)
            if foulPlay['players'][0]['teamId'] == meta[meta['onOffense']+"Id"]:
                return True
        elif (8,11) in allEventDetails or (8,5) in allEventDetails:
            #technical foul, or inbounds foul, dont mind this, the made shot still ends the possession
            return True
        elif (8,15) in allEventDetails or  (8,14) in allEventDetails:
            #flagrant 1 or 2, if the fouling team didnt have it return false
            #thanks giannis, https://www.youtube.com/watch?v=GWajqr55HFg
            if debug:
                print("flagrant", meta[meta['onOffense']+"Id"], play['players'][0]['teamId'])
            if meta[meta['onOffense']+"Id"] == play['players'][0]['teamId']:
                return False
            else:
                return True
        elif (1, 10) in allEventDetails:
            #ft 1 of 1 made, so wait for that one
            return False
        elif (2,10) in allEventDetails:
            if debug:
                print("missed ft")
            #coulda been another type of foul, but the ft was still missed
            #1459532, made layup, same time foul off the ball, got to shoot ft
            return False
        
        else:
            if debug:
                print("no shot scenarios caught this", play['playText'], play['playEvent']['playEventId'], eid)
            if(8,6) in allEventDetails:
                if debug:
                    print("away from play foul")
            return True
    
    #made ft, is it n of n?
    if eid == 1:
        if thisDetailId == 10 or thisDetailId == 12 or thisDetailId == 15:
            #was this an away from play foul in the last 2 minutes if so then offense keeps it, otherwise its over
            if  not (play['time']['minutes'] < 2 and play['period'] >= 4 and (8,6) in allEventDetails):
                return True
            
    if eid == 9 and thisDetailId == 7 and (8,2) in allEventDetails and 3 in allEventIds:
        #there was a made shot and shooting foul, but this event is a lane violation, so the possession ends here, no free throw event
        return True
    
    if thisDetailId == 16 and eid == 1 and (7,44) in allEventDetails:
        #technical foul too many players, switch ball if you have
        if meta[meta['onOffense']+"Id"] != play['players'][0]['teamId']:
            return True
    
    
    #jump ball, did offense hold on?
    if eid==12:
        jump = getJumpWinner(play, sec, meta)
        if jump == 0 and meta['onOffense'] == "away" or jump == 1 and meta['onOffense'] == "home":
            #wrong team
            #sometimes this comes with a turnover event, so the loss of poss is actually on that
            if debug:
                print("jump winner on wrong team", meta['onOffense'], jump)
            if (7,2) not in allEventDetails and (7,1) not in allEventDetails: 
                return True

    return False

def swapOffense(meta):
    if meta['onOffense'] == "home":
        meta['onOffense'] = "away"
    elif meta['onOffense'] == 'away':
        meta['onOffense'] = "home"
    return meta

def getStatsFromPlay(play, poss, meta):
    
    #unfortunate hack but they just get the plays out of order
    #http://www.si.com/pbp/liveupdate?json=1&sport=basketball%2Fnba&id=1460471&box=true&pbp=true&linescore=true
    if meta['gameId'] == 1460471 and play['playId'] == "297":
        poss.defTeamPts += 1
        poss.points -= 1
    
    #weird extra point
    #http://www.si.com/pbp/liveupdate?json=1&sport=basketball%2Fnba&id=1459771&box=true&pbp=true&linescore=true
    if meta['gameId'] == 1459771 and play['playId'] == "438":
        poss.points += 1

    eid = play['playEvent']['playEventId']
    thisDetailId = 0 if 'playDetailId' not in play['playEvent']['playDetail'] else play['playEvent']['playDetail']['playDetailId']
    if eid == 1:
        #free throw
        
        #make sure this wasnt a technical for the other team
        if play['playEvent']['playDetail']['playDetailId'] == 16:
            tid = play['players'][0]['teamId']
            if tid == meta['homeId'] and meta['onOffense'] == 'away' or tid == meta['awayId'] and meta['onOffense'] == 'home':
                #put this in the meta and add as well
                poss.defTeamPts += 1
            else:
                poss.points += 1
        #ft made
        else:
            poss.points += 1
    elif eid == 2:
        #missed ft, if its not the last lets subtrct the oreb which will be added
        if thisDetailId in [11, 13, 14]:
            poss.oRebs -= 1
    elif eid == 3:
        #made shot
        poss.points += play['pointsScored']
        if "assist" in play['playText']:
            poss.assist = getAssistFromPlay(play, meta)
    elif eid == 4:
        if play['isBlocked'] ==1:
            poss.blks = poss.blks + 1
    elif eid == 5:
        #offensive rebound
        #should i count team offensive rebounds with no player?
        # sometimes they come after missed free throws which is dumb, but sometimes they come in the middle of play
        # lets count them all, and when someone misses a free throw which isnt last, well subtract it (above)
        poss.oRebs += 1
        
    elif eid == 7:
        #turnover
        poss.turnover = True
        if "steals" in play['playText']:
            poss.steal = True
    elif eid == 8:
        #foul
        if thisDetailId not in [4,26]:
            #this probaby needs more
            poss.dFouls += 1
    #other stats
    if play['isFastBreak']:
        #not really sure what SI constitutes as a fast break, but sure this info might be useful
        poss.fastBreak = True
        
    return poss

def siToCDPId(playId,detailId, poss):
    #use my own state ids so i can potentially scrape from other sites to verify

    if playId == 1:
        if detailId == 10 or detailId == 20:
            return 6
        if detailId == 12 or detailId == 19 or detailId == 24:
            return 7
        if detailId == 15:
            return 8
    if playId == 3:
        #made shot
        if poss.points == 3:
            return 3
        return 2
    if playId == 6:
        #dreb
        return 1
    
    if playId == 7 or playId ==8 or playId == 9:
        #9 is a violation, but will be a dead ball, 8 is a foul, so essentially like a dead-ball turnovers
        if poss.steal:
            return 5
        return 4
    if playId == 12:
        #counting jump ball loss as steal, sorta the same live ball possession switch, defense not back
        return 5
    if playId == 15:
        return 9
    print(playId, detailId, poss)
    raise ValueError("unaccounted")
    return

def getStarters(plays, meta):
    starters = {"home": [], "away": []}
    for play in plays:
        if play['playText'] == "Starting Lineup":
            tId = play['players'][0]['teamId']
            if tId == meta['awayId']:
                starters['away'].append(play['players'][0]['playerId'])
            else:
                starters['home'].append(play['players'][0]['playerId'])
    return starters

def prepGame(data):
    '''get the game meta, and group all plays by their second for easy retreival later
        also grab the starters and pull those plays out of the array
    '''
    pbp = data['apiResults'][0]['league']['season']['eventType'][0]['events'][0]['pbp']
    evnts = data['apiResults'][0]['league']['season']['eventType'][0]['events'][0]
    meta = getMeta(evnts)
    by_seconds = collections.defaultdict(list)
    
    #batch the plays by qtr/clock
    for play in pbp:     
        key = str(play['period']) + "-" + str(play['time']['minutes'] )+ "-" + play['time']['seconds']
        by_seconds[key].append(play)

    return (meta, by_seconds, pbp)
        
def getKey(play):
    return str(play['period']) + "-" + str(play['time']['minutes'] )+ "-" + play['time']['seconds']

def getNextShotId():
    global storedShots
    return len(shots.index) + storedShots

def getNextAssistId():
    global storedAssists
    return len(assists.index) + storedAssists

def getAssistFromPlay(play, meta):
    ast = {'foul':False, 'gameId':meta['gameId'], "pid":play['players'][1]['playerId'], "scorerId":play['players'][0]['playerId'],
               'pts':play['pointsScored'], 'fastBreak':play['isFastBreak']==True, 'qtr':play['period']}
    ast['x'] = play['shotCoordinates']['x']
    ast['y'] = play['shotCoordinates']['y']
    ast['clock'] = float(60*play['time']['minutes'])+float(play['time']['seconds'])
    ast['index'] = getNextAssistId()
    allAst.append(ast)
    return ast['index']

def getShotFromPlay(play, meta):
    global allShots
    ''' makes or missed on field goals  lets add these to the shots df, and return their ids
    '''
    
    if 'x' in play['shotCoordinates']:
        if 'shotAttemptPoints' in play:
            eid = play['playEvent']['playEventId']
            thisDetailId = 0 if 'playDetailId' not in play['playEvent']['playDetail'] else play['playEvent']['playDetail']['playDetailId']
            sid = getNextShotId()
            shot = {'foul':False, 'isFreeThrow': False, 'gameId' : meta['gameId']}
            shot['clock'] = float(60*play['time']['minutes'])+float(play['time']['seconds'])
            shot['qtr'] = play['period']

            shot['pid'] = play['players'][0]['playerId']
            if play['shotAttemptPoints'] == 1:
                shot['isFreeThrow'] = True
                shot['make'] = eid == 1
                shot['pts'] = 1 if eid == 1 else 0
                shot['x'] = -1; shot['y'] = -1
                
            else:
                #not a free throw
                shot['x'] = play['shotCoordinates']['x']
                shot['y'] = play['shotCoordinates']['y']
                shot['make'] = 'pointsScored' in play and play['shotAttemptPoints'] == play['pointsScored']
                if 'pointsScored' in play:
                    shot['pts'] = play['pointsScored']
                else:
                    shot['pts'] = 0
            #put shot in df

            #pp.pprint(shot)
            if len(shot.keys()) !=10:
                raise ValueError("keys")
            allShots.append(shot)
            shot['index'] = getNextShotId()
            return shot['index']
    return -1

def doSub(play, onCourt, meta):
    #turns out SI doesnt get substitutions at start and end of qts, so this is pointless, wont be keeping track of whos on the court
    off = play['players'][1]
    on = play['players'][0]
    subTeam = "away" if play['players'][1]['teamId'] == meta['awayId'] else "home"
    #print(play['time']['seconds'],subTeam, off['playerId'], on['playerId'], onCourt)
    #offIndex = onCourt[subTeam].index()
    onCourt[subTeam].remove(off['playerId'])
    onCourt[subTeam].append(on['playerId'])
    #print(subTeam, off['playerId'], on['playerId'], onCourt)
    return onCourt

def resetData():
    global shots
    global assists
    global possessions
    global files
    global games 
    shots = pd.DataFrame(columns=["pid", "x", "y", "make", "foul",  "pts", "gameId", "qtr", "clock", "isFreeThrow"])
    assists = pd.DataFrame(columns =["pid", "scorerId", "x", "y", "foul", "pts", "gameId", "qtr", "clock", "isFastBreak"])
    possessions = pd.DataFrame(columns = ["off", "def", "startTime", "endTime", "endText", "dur","points", "actionPlayer", "turnover","oRebs","blks", "assist","steal", "startState", "endState", "fastBreak", "qtr","dFouls", "defTeamPts", "shots", "gameId"])
    games = pd.DataFrame(columns = ['away','home', 'awayScore', 'homeScore', 'date', 'gameId','awayPoss', 'homePoss', 'periods'])
    path = "games/"+year+"/"
    files = [path+f for f in os.listdir(path) if "reg" in f]
    print(len(files))


def storeWhatYouGot():
    global count
    global storedPoss
    global storedAssists
    global storedShots
    global year

    print("storing to "+"data/"+year+"/poss."+str(count)+".csv")
    possessions.to_csv("data/"+year+"/poss."+str(count)+".csv", index=False)
    shots.to_csv("data/"+year+"/shots."+str(count)+".csv", index=False)
    assists.to_csv("data/"+year+"/assists."+str(count)+".csv", index=False)
    games.to_csv("data/"+year+"/games."+str(count)+".csv", index=False)
    storedPoss += len(possessions.index)
    storedShots += len(shots.index)
    storedAssists += len(assists.index)
    count += 1
    #possessions.head()
    print("storing to db", len(possessions.index), len(shots.index), len(assists.index), storedPoss, storedShots, storedAssists)


def findWhere(sec, details):
    #returns the first play in sec where the id and detailId match
    for play in sec:
        if play['playEvent']['playEventId'] == details[0] and play['playEvent']['playDetail']['playDetailId'] == details[1]:
                return play
    return False


def grabPossessions(by_seconds, meta, plays):
    global shots
    global assists
    global possessions
    global allAst
    global allShots
    global allPoss
    
    ends = []
    invalidAlone = []
    homeScore = 0 
    awayScore = 0
    homePoss = 0
    awayPoss = 0
    qtr = 1
    qtrBall = []
    #print meta
    #get the starters
    onCourt = getStarters(plays[0:10], meta)
    if len(onCourt['home']) != 5 or len(onCourt['away']) != 5:
        raise Exception("who are the starters")


    plays = plays[10:]
    
    if debug:
        print meta

    noTipEvents = [1460014, 1577738, 1571495, 1577641,1570488, 1570835, 1570849]

    if plays[1]['playEvent']['playEventId'] == 12 or plays[1]['playEvent']['playEventId'] == 9 or meta['gameId'] in noTipEvents:
        #12 regular jump, 9 violation
        clock = float(60*plays[1]['time']['minutes'])+float(plays[1]['time']['seconds'])
        p=plays[1]
        sec = by_seconds[getKey(p)]
        jw = getJumpWinner(plays[1], sec, meta)
        startState = 9
        if jw == 0:
            meta['onOffense'] = "home"
            qtrBall = ["home", "away", "away", "home"]
        elif jw == 1:
            meta['onOffense'] = "away"
            qtrBall = ["away", "home", "home", "away"]
        #dont assign otherwise, would like it to throw a ValueError
    
    if 'onOffense' not in meta:
        raise ValueError("nobody won the tip?")

    j=2
    while j < len(plays):
        
        data = [None,  None,       clock,        -1,        "",    -1,       0,             -1,      False,      0,     0,       -1,  False,   startState,       None,       False,   qtr,       0,            0,      [], meta['gameId']]
        index=["off", "def", "startTime", "endTime", "endText", "dur","points", "actionPlayer", "turnover","oRebs","blks", "assist","steal", "startState", "endState", "fastBreak", "qtr","dFouls", "defTeamPts", "shots", "gameId"]
        #print(len(data), len(index))
        poss = pd.Series(data, index)
        possessionOver = False

        while not possessionOver:
            play = plays[j]
            sec = by_seconds[getKey(play)]
            clock = float(60*play['time']['minutes'])+float(play['time']['seconds'])
            if poss.startTime == -1:
                poss.startTime = clock
            
            if meta['onOffense'] == None:
                if play['playEvent']['playEventId'] == 14:
                    if play['period'] > 4:
                        #we want the next one
                        j += 1
                        play = plays[j]
                        sec = by_seconds[getKey(play)]
                if  play['playEvent']['playEventId'] == 12:
                    jw = getJumpWinner(play, sec, meta)
                    if jw < 0: 
                        raise ValueError("no winner for ot jump?")
                    meta['onOffense'] = "home" if jw == 0  else "away" 
                elif meta['gameId'] == 1459504 and qtr == 5:
                    #this game doesnt even have a jump at the start of ot?
                    meta['onOffense'] = "away"
                elif meta['gameId'] == 1460427 and qtr == 5:
                    meta['onOffense'] = "away"
            defense = "home" if meta['onOffense'] == "away" else "away"
            poss.off = meta[meta['onOffense']+"Id"]
            poss['def'] = meta[defense+"Id"]
            
            #si bad data killing my dreams on on court tracking
            #if play['playEvent']['playEventId'] == 10:
                #onCourt = doSub(play, onCourt, meta)
                
            possessionOver = isPossessionOver(play, sec, meta)
            endOfQtr = whichEndOfQtr(play, meta)
            poss = getStatsFromPlay(play, poss, meta)
            shotId = getShotFromPlay(play, meta)
            
            if shotId > -1:
                poss.shots.append(shotId)
            if possessionOver:
                
                poss.endTime = clock
                poss.dur = poss.startTime - poss.endTime
                det = 0 if 'playDetailId' not in play['playEvent']['playDetail'] else play['playEvent']['playDetail']['playDetailId']
                startState = poss.endState = siToCDPId(play['playEvent']['playEventId'], det, poss) 
                poss.endText = play['playText']
                
                #is this possession valid?
                #use score in api to verify your count is correct
                if meta['onOffense'] == "home":
                    homePoss += 1
                    homeScore += poss.points
                    awayScore += poss.defTeamPts
                elif meta['onOffense'] == "away": 
                    awayPoss += 1
                    awayScore += poss.points
                    homeScore += poss.defTeamPts

                if debug:   
                    print("poss over",meta[meta['onOffense']+"Name"], clock,poss.off, play['playText'], poss.points, poss.defTeamPts, awayScore, homeScore)
                if homeScore != play['homeScore'] or awayScore != play['visitorScore']:

                    #badData for exceptions when data is actually wrong in pbp
                    badData = [(1570449, "23")]
                    if (meta['gameId'], play['playId'] ) not in badData:
                        print("my count", awayScore, homeScore, "real", play['visitorScore'],  play['homeScore'])
                        pp.pprint(play)
                        raise ValueError("guess we got the possession wrong")
                
                meta = swapOffense(meta)

                if -1< endOfQtr < 4:
                    qtr = endOfQtr +1
                    #quarter possessions based of jump winner
                    clock = 720
                    meta['onOffense'] = qtrBall[endOfQtr]
                elif endOfQtr >=4 and j != len(plays)-1:
                    clock = 300
                    qtr = endOfQtr +1
                    meta['onOffense'] = None
                             
                allPoss.append(poss)
            
            j += 1
            
        #print(len(poss))
    
    possessions = possessions.append(allPoss)
    assists = assists.append(allAst)
    shots = shots.append(allShots)
    #games = pd.DataFrame(columns = ['away','home', 'awayScore', 'homeScore', 'date', 'gameId','awayPoss', 'homePoss', 'periods'])
    games.loc[len(games.index)] = [meta['awayId'], meta['homeId'] , awayScore, homeScore, meta['date'], meta['gameId'], awayPoss, homePoss, endOfQtr]
    print("game comp", len(allPoss), len(allAst), len(allShots), len(possessions.index), len(shots.index), len(assists.index))


if __name__ == "__main__":
    global allPoss
    global allAst
    global allShots
    global year
    global debug
    global storedPoss
    global storedAssists
    global storedShots
    year = settings.year
    debug = settings.debug
    start = settings.start
    buff = settings.buff
    resetData()
    storedShots = 0
    storedPoss = 0
    storedAssists = 0
    count = 0
    if debug:
        print(len(files))

    while start < len(files):
    	td = 0
    	allPoss = []
    	allAst = []
    	allShots = []

    	for f in files[start:start+buff]:
    	    allPoss = []
    	    allAst = []
    	    allShots = []
    	    print(f, start+td)
    	    td +=1
    	    with open(f) as infile:
    	        data = json.load(infile)
    	        meta, by_secs, plays = prepGame(data)
    	        grabPossessions(by_secs, meta, plays)

    	storeWhatYouGot()
    	resetData()
    	start += buff
    print("all done")