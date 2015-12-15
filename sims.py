import numpy as np
import models

def simTransGame(awayTime, awayTransO, awayTransD,  homeTime, homeTransO, homeTransD):
	'''
		sim a game using transitional matrix model, based on how a possession starts
		how will it end?
		time independent of reward, weibull distribution
		alternating renewal-reward process
	'''
	homePoints = 0
	awayPoints = 0
	hometop = 0
	awaytop = 0
	homenpos = 0
	awaynpos = 0
	rewards = [0,0,2,3,0,0,1,2,3,0]
	homeTrans = (homeTransO + awayTransD)/2
	awayTrans = (awayTransO + homeTransD)/2

	for q in range(1,5):
		time = 720
		state = 9

		if q == 1 or q == 3:
			#give home team poss
			top = np.random.weibull(homeTime[0], 1)*homeTime[2]
			hometop += top
			time -= top
			homenpos += 1
			state = simTransition(homeTrans, state)
			homePoints += rewards[state]

		while time > 3:

			#do away possession
			top = np.random.weibull(awayTime[0], 1)*awayTime[2]
			awaytop += top
			time -= top
			awaynpos += 1
			state = simTransition(awayTrans, state)
			awayPoints += rewards[state]

			if time < 3:
				#no time
				break

			#do home possession
			top = np.random.weibull(homeTime[0], 1)*homeTime[2]
			hometop += top
			time -= top
			homenpos += 1
			state = simTransition(homeTrans, state)
			homePoints += rewards[state]
	return (awayPoints, homePoints, awaytop, hometop, awaynpos, homenpos)


def simTransition(matrix, state):
    outcomes = matrix[state]
    outcomes = outcomes/outcomes.sum()
    o = np.random.multinomial(1, outcomes, size=1)
    return np.where(o==1)[1][0]



def simGame(away, home):
    awayTime = models.getTeamTimeDist(away, "away")
    homeTime = models.getTeamTimeDist(home, "home")
    homeTransO = models.getTeamTrans(home, "off", "home")
    homeTransD = models.getTeamTrans(home, "def", "home")
    awayTransO = models.getTeamTrans(away, "off", "away")
    awayTransD = models.getTeamTrans(away, "def", "away")
    num = 2000
    a = 0.0
    h = 0.0
    awaytop = 0
    hometop = 0
    awaynpos = 0
    homenpos = 0
    for i in range(0, num):
        g = simTransGame( awayTime, awayTransO, awayTransD, homeTime, homeTransO, homeTransD)
        a += g[0]
        h += g[1]
        awaytop += g[2]
        hometop += g[3]
        awaynpos += g[4]
        homenpos += g[5]

    return(a/num, h/num, awaytop[0]/num, hometop[0]/num, awaynpos/num, homenpos/num)