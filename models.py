import pandas as pd
import teams
import scipy.stats as s
import numpy as np
import matplotlib.pyplot as plt
import teams    
import settings

def plotTeamTimeDist(id):
    team = teams.getTeamById(id)
    teamPos= possessions[(possessions['off'] == id) & (possessions['dur'] >= 0)]
    tm = teamPos['dur'].values
    if len(tm) == 0:
        print(id, len(tm))
        raise ValueError("wha")
    mean = sum(tm)/len(tm)
    textstr = "mean="+str(round(mean, 2))
    p0, p1, p2=s.weibull_min.fit(tm, floc=0)
    ydata=s.weibull_min.pdf(np.linspace(0, 50, 100), p0, p1, p2)
    plt.plot(np.linspace(0, 50, 100),ydata, '-')
    plt.title(team['name'] +" Weibull")
    plt.hist(tm,24, normed=1)
    plt.text(35, .04, textstr)
    #plt.show()
    plt.savefig("vis/"+team['name']+"Weibull.png")
    plt.clf()

def getTeamTimeDist(id, homeOrAway):
    team = teams.getTeamById(id) if type(id) == int else teams.getTeamByName(id)
    teamPos= possessions[(possessions['off'] == team['id'])]
    if homeOrAway is not None:
        validGames = [int(game[1]['gameId']) for game in games.iterrows() if game[1][homeOrAway] == team['id']]
        teamPos = pd.DataFrame([p[1] for p in teamPos.iterrows() if p[1]['gameId'] in validGames])
    tm = teamPos['dur'].values
    mean = sum(tm)/len(tm)
    textstr = "mean="+str(round(mean, 2))
    return s.weibull_min.fit(tm, floc=0)

def getTeamTrans(id, offenseOrDefense, homeOrAway):
    #get transitional matrix for a team, filter by offensive or defensive possessions
    global ends
    team = teams.getTeamById(id) if type(id) == int else teams.getTeamByName(id)
    thisTeam = possessions[possessions[offenseOrDefense] == team['id']]
    if homeOrAway is not None:
        validGames = [int(game[1]['gameId']) for game in games.iterrows() if game[1][homeOrAway] == team['id']]
        thisTeam = pd.DataFrame([p[1] for p in thisTeam.iterrows() if p[1]['gameId'] in validGames])
    ends = np.zeros(shape=(10,10))
    thisTeam.apply(getTransMatrix, axis=1)
    ends = (ends/ends.sum())*100
    return ends

    
def filterHomeAway(poss, homeAway):
    print(homeAway)

def getTransMatrix(poss):
    ends[int(poss.startState)][int(poss.endState)] += 1
    return 

year = settings.year
#sa = []
#aa = []
pa = []
ga = []


for i in range(0, 5):
    possPath = "data/"+year+"/poss."+str(i)+".csv"
    gamesPath = "data/"+year+"/games."+str(i)+".csv"
    #astPath = "data/"+year+"/assists."+str(i)+".csv"
    #shotPath = "data/"+year+"/shots."+str(i)+".csv"
    try:
        #shotAdd = pd.read_csv(shotPath)
        #astAdd = pd.read_csv(astPath)
        gamesAdd = pd.read_csv(gamesPath)
        possAdd = pd.read_csv(possPath)
    except IOError:
        if settings.debug:  
            print("nofile", possPath)
        continue
    pa.append(possAdd)
    ga.append(gamesAdd)
    #sa.append(shotAdd)
    #aa.append(astAdd)

possessions = pd.concat(pa)
games = pd.concat(ga)
#shots = pd.concat(sa)
#assists = pd.concat(aa)