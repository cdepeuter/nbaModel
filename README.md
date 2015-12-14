#NBA possession based modeling

This project scrapes possession data from play-by-play logs on si.com, and uses the scraped data to create a model that predicts outcomes of NBA games.  More description of the model is available in modelResults.ipynb.

##Building yourself

To run locally:
	1. change your desired year in settings.py (2014,2015 valid)
	2. run scrape.py
	3. run parse.py
		-The last build was dec.8, sometimes there is bad data in the play by plays, so parsing may result in confusing the possession identifying function,
		-Any games up to this date should work, but after some more hacks included in parse.isPossessionOver or parse.getJumpWinner to bring clarity to situation.
		-When determining a hack it is useful to view the video play by play available for the game (http://stats.nba.com/game/#!/0021400731/playbyplay/)
	4. After parse.py you are all set up to simulate games. Some examples on how to run sims available in modelResults.ipynb
	