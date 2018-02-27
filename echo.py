from flask import Flask
from flask_ask import Ask, statement, question, session
import json, requests, time
from coinmarketcap import Market
from steem import Steem
from steem.account import Account
from steem.instance import set_shared_steemd_instance
from steem.steemd import Steemd

cmc = Market()
session = requests.Session()
app = Flask(__name__)
ask = Ask(app, "/steem_assistant")
s = Steem(nodes=["https://api.steemit.com", "https://rpc.buildteam.io"])
steemd_nodes = [
    'https://api.steemit.com/',
    'https://gtg.steem.house:8090/',
    'https://steemd.steemitstage.com/',
    'https://steemd.steemgigs.org/'
    'https://steemd.steemit.com/',
]
set_shared_steemd_instance(Steemd(nodes=steemd_nodes)) # set backup API nodes

def session_post(url, post):
	headers = {
		'User-Agent': 'Steem-Assistant'
	}

	return session.post(url, data = post, headers = headers, timeout = 30)

### ### ### ### ### ### ### ### ### ### THIS IS WHERE FLASK DECORATED FUNCTIONS START ### ### ### ### ### ### ### ### ### ### 

@app.route('/')
def homepage():
	return "Placeholder page for Steem-Assistant"

# This is what alexa will say if you ask echo to "Use Steem Assistant"
@ask.launch
def start_skill():
	welcome_msg = 'Welcome to Steem Assistant, what can I assist you with?'

	return question(welcome_msg)

# Read outs the top 10 posts on /trending (their titles & authors)
@ask.intent("TrendingCheckIntent")
def check_trending_posts():
	data = s.get_discussions_by_trending({"limit":"10"})

	posts = {}
	for _ in range(len(data)):
		posts[data[_]["title"]] = data[_]["author"]

	response_str = ""
	for post in posts:
		added_str = '. . . . .%s... ,by %s...' %(post, posts[post])
		response_str += added_str

	response = "The current trending posts on steem are: %s" %(response_str)

	return statement(response)

# Reads out specific post from top 10 on /trending (title & author)
@ask.intent("TrendingSpecificPostIntent")
def read_trending_post(number):
	numbers_dict = {
	"1st" : 1,
	"2nd" : 2,
	"3rd" : 3,
	"4th" : 4,
	"5th" : 5,
	"6th" : 6,
	"7th" : 7,
	"8th" : 8,
	"9th" : 9,
	"10th" : 10,
	}

	data = s.get_discussions_by_trending({"limit":"10"})
	index = numbers_dict[number]
	title = data[index-1]['title']
	author = data[index-1]['author']

	response = "The %s post is %s, by %s" %(number,title,author)

	return statement(response)

# Returns a price of a given coin.
@ask.intent("PriceCheckIntent")
def check_price(coin):
	coin = coin.replace(" ", "-").lower()
	coin = coin.replace("steam", "steem")
	response = requests.get("https://api.coinmarketcap.com/v1/ticker/?limit=500")
	data = json.loads(response.text)
	for x in data:
		if x['id'] == coin or x['symbol'].lower() == coin:
			price = x['price_usd']
			name = x['name']
			available = True
			break
		else:
			available = False
	if available:	
		response = "The current price of %s is %s USD" %(name, price)
	else:
		response = "The coin you've asked for doesn't exist or is unavailable. Sorry."

	return statement(response)

if __name__ == '__main__':
	app.run(port=80)
