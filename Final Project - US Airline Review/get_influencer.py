# To run this code
#
# mkdir output
# python get_influencer.py -t tweets.json -a @AmericanAir

import sys
import json
import argparse
import pandas as pd
import networkx as nx
from sklearn.preprocessing import StandardScaler

def get_parser():
    """Get parser for command line arguments."""
    parser = argparse.ArgumentParser(description="Twitter Influencer")
    parser.add_argument("-t",
                        "--tweets",
                        dest="tweets",
                        help="Tweets/Dict")
    parser.add_argument("-a",
                        "--airline",
                        dest="airline",
                        help="Airline/Twitter Handle")
    return parser

def read_json(file):
	f = open(file)
	line = f.read()
	f.close()
	return json.loads(line)

def write_csv(df, airline):
	df.to_csv('output/{}.csv'.format(airline))

def get_user_central(air_tweet):
	n = len(air_tweet)
	user1 = []
	user2 = []
	tweet_type = []
	tweet_text = []
	for i in range(n):
		user_rt = ''
		user_reply = ''
		user_tw = air_tweet[i]['user']['screen_name']
		txt = air_tweet[i]['text']
		if air_tweet[i]['entities']['user_mentions']: 
			user_mentioned = [m['screen_name'] for m in air_tweet[i]['entities']['user_mentions']] #store all @ screen names 
			if 'retweeted_status' in air_tweet[i].keys(): 
				user_rt = air_tweet[i]['retweeted_status']['user']['screen_name']
				user1.append(user_tw)
				user2.append(user_rt)
				tweet_type.append('RT')
				tweet_text.append(txt)
				user1.append(user_rt)
				user2.append(user_rt)
				tweet_type.append('tweet')
				tweet_text.append(air_tweet[i]['retweeted_status']['text'])
			elif air_tweet[i]['in_reply_to_screen_name']:
				user_reply = air_tweet[i]['in_reply_to_screen_name']
				user1.append(user_tw)
				user2.append(user_reply)
				tweet_type.append('reply')
				tweet_text.append(txt)
			for u in [user for user in user_mentioned if (user != user_rt and user != user_reply)]:
				user1.append(user_tw)
				user2.append(u)
				tweet_type.append('mention')
				tweet_text.append(txt)
		else:
			user1.append(user_tw)
			user2.append(user_tw)
			tweet_type.append('tweet')
			tweet_text.append(txt)
	tweet_df = pd.DataFrame({'user1':user1,'user2':user2,'type':tweet_type,'text':tweet_text})
	tweet_df = tweet_df.drop_duplicates()[['user1','user2','type']]
	tweet_link = tweet_df.groupby(['user1','user2']).count().reset_index()
	user_from = tweet_link.user1.tolist()
	user_to = tweet_link.user2.tolist()
	weight = tweet_link.type.tolist()
	G = nx.DiGraph()
	for i in range(len(user_from)):
		G.add_edge(user_from[i],user_to[i], weight = weight[i])
	users = G.nodes
	degree = nx.degree_centrality(G)
	between = nx.betweenness_centrality(G)
	close = nx.closeness_centrality(G)
	user_stats_central = pd.DataFrame(zip(users,degree.values(),between.values(),close.values()),columns = ['user_name','degree','between','close'])
	return user_stats_central

def get_user_api(air_tweet):
	n = len(air_tweet)
	user_stats = {}
	for i in range(n):
		user_tw = air_tweet[i]['user']['screen_name']
		if 'retweeted_status' in air_tweet[i].keys():
			user_rt = air_tweet[i]['retweeted_status']['user']['screen_name']
			if user_rt not in user_stats:
				user_stats[user_rt] = {}
				user_stats[user_rt]['listed_count'] = air_tweet[i]['retweeted_status']['user']['listed_count']
				user_stats[user_rt]['followers_count'] = air_tweet[i]['retweeted_status']['user']['followers_count']
				user_stats[user_rt]['statuses_count'] = air_tweet[i]['retweeted_status']['user']['statuses_count']
		if user_tw not in user_stats:
			user_stats[user_tw] = {}
			user_stats[user_tw]['listed_count'] = air_tweet[i]['user']['listed_count']
			user_stats[user_tw]['followers_count'] = air_tweet[i]['user']['followers_count']
			user_stats[user_tw]['statuses_count'] = air_tweet[i]['user']['statuses_count']
	user_stats_api = pd.DataFrame.from_dict({i: user_stats[i] for i in user_stats.keys()},orient='index').drop_duplicates()
	user_stats_api = user_stats_api.reset_index()
	user_stats_api.columns = ['user_name','listed_count','followers_count','statuses_count']
	return user_stats_api  

def get_top_influencer(central, api):
	user_stats_overall = api.merge(central,left_on='user_name',right_on='user_name')
	w = [0.3,0.25,0.15,0.3]
	user_factor = user_stats_overall
	user_factor['central'] = (user_factor.degree + user_factor.between + user_factor.close)
	user_factor = user_factor.drop(['degree','between','close'],axis = 1)
	scaler = StandardScaler() 
	user_factor_norm = pd.DataFrame(scaler.fit_transform(user_factor[['listed_count','followers_count','statuses_count','central']]))
	user_factor_norm['user_name'] = user_factor['user_name']
	user_factor_norm['score'] = user_factor_norm.iloc[:,0]*w[0] + user_factor_norm.iloc[:,1]*w[1] + user_factor_norm.iloc[:,2]*w[2] + user_factor_norm.iloc[:,3]*w[3]
	user_factor_norm.columns = ['listed_count','followers_count','statuses_count','central','user_name','score']
	result = user_factor_norm[['user_name','score','listed_count','followers_count','statuses_count','central']].sort_values(by = 'score', ascending = False)[:50]
	return result

if __name__ == '__main__':
	parser = get_parser()
	args = parser.parse_args()
	tweets = read_json(args.tweets)
	tweets_airline = tweets[args.airline]
	user_central = get_user_central(tweets_airline)
	user_api = get_user_api(tweets_airline)
	final = get_top_influencer(user_central, user_api)
	write_csv(final, args.airline)
