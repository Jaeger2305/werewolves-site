'''
Redis is a key value database that's held entirely in memory (with the advantage of disk backup)
Keys can contain identifiers:
	"game:123"	# key for a game that includes the ID for easy searcing
Values can be hashes, which is basically another set of key-values that are good at representing objects
	"game:123" 	=> "name"	 	=>	"myRoom"
				=> "players"	=>	"player:1|player:2|player:3"
				...
In the case above, the players key contains a string of player IDs. If you split the string with "|" you can then use them as keys
	"player:1"	=>	"name"		=>	"Patrick"
				=>	"character"	=>	"werewolf"
				...

For performance reasons, redis stores everything as byte arrays, so you need to convert it into the format you want
This will often be a string, so try my_str.decode("utf-8"), or look at something else if you don't want a string (or convert from a string)

SwampDragon uses redis' PubSub method to broadcast information through the routers.
I started doing the nitty gritty redis stuff, but the models should be easier once I get my head around them

'''


import redis

ww_redis_db = redis.StrictRedis(host='localhost', port=6379, db=0)