from flask import Flask
from flask_ask import Ask, statement, question, session
import json, requests, time, random
from steem import Steem
from steem.account import Account
from steem.instance import set_shared_steemd_instance
from steem.steemd import Steemd

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

# Is used to read out information about specific posts.
def read_post(index, data, name):
	data = data[index-1]
	title = data['title'].replace('@', '')
	author = data['author']
	tags_list = json.loads(data['json_metadata'])['tags']
	tags = ', '.join(tags_list[:-1])
	if len(tags_list) > 1:
		tags = tags + ", and " + str(tags_list[-1])
		amount = "tags"
	else:
		tags = tags_list[0]
		amount = "tag"
	votes = data['net_votes']
	comments = data['children']
	payout = data['pending_payout_value'].replace('SBD', '').rstrip('0').rstrip('.')

	response = "The %s is: %s, by %s. It's been posted under the following %s: %s... It has gathered a total of %s upvotes with a value of %s Steem Dollars, and has been commented on %s times." %(name, title, author, amount, tags, votes, payout, comments)

	return response

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
@ask.intent("TopCheckIntent")
def check_trending_posts(category):
	posts = {}
	for _ in range(len(data)):
		posts[data[_]["title"]] = data[_]["author"]

	response_str = ""
	for post in posts:
		added_str = '. . . . .%s... ,by %s...' %(post, posts[post])
		response_str += added_str

	try:
		if category.lower() == "trending":
			data = s.get_discussions_by_trending({"limit":"10"})
		elif category.lower() == "hot":
			data = s.get_discussions_by_hot({'limit':'10'})
		else:
			data = s.get_discussions_by_created({"limit":'10'})
			category = "new"

		response = "The current %s posts on steem are: %s" %(category, response_str)
	except (TypeError, AttributeError):
		return statement("Sorry, I did not hear you clearly or you didn't provide enough arguments. Please try again.")

	return statement(response)

# Reads out specific post from top 10 on /trending, /hot or /created (title & author)
@ask.intent("SpecificPostIntent")
def get_trending_post(number, category):
	numbers_dict = {"1st" : 1,"2nd" : 2,"3rd" : 3,"4th" : 4,"5th" : 5,"6th" : 6,"7th" : 7,"8th" : 8,"9th" : 9,"10th" : 10}

	try:
		response_str = str(number + " post from " + category)
		index = numbers_dict[number]
		if category.lower() == "trending":
			data = s.get_discussions_by_trending({"limit":"10"})
		elif category.lower() == "hot":
			data = s.get_discussions_by_hot({'limit':'10'})
		else:
			data = s.get_discussions_by_created({"limit":'10'})
			response_str = str(number + " post on steem ")
	except (TypeError, AttributeError):
		return statement("Sorry, I did not hear you clearly or you didn't provide enough arguments. Please try again.")
	

	return statement(read_post(index, data, response_str))

# Reads out a random post from a new, hot or trending. 
@ask.intent("LuckyPostIntent")
def read_lucky_post(category):
	try:
		response_str = str("Lucky post from " + category)
		if category.lower() == "trending":
			data = s.get_discussions_by_trending({"limit":"100"})
		elif category.lower() == "hot":
			data = s.get_discussions_by_hot({'limit':'100'})
		else:
			data = s.get_discussions_by_created({"limit":'100'})
			response_str = str("Lucky post ")
	except (TypeError, AttributeError):
		return statement("Sorry, I did not hear you clearly or you didn't provide enough arguments. Please try again.")

	index = random.randint(0,100)

	return statement(read_post(index, data, response_str))

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
