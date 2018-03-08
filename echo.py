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

nickname = "ned" # THIS WILL BE INTEGRATED WITH STEEMCONNECT WHEN I GET A HOLD OF HOW TO USE IT, FOR NOW, FOR TESTING PURPOSES, THE NICKNAME IS HARDCODED.

class SteemUser:

	def __init__(self, username):
		self.username = username
		self.session = Account(self.username, steemd_instance=s)

		self.wallet = {
		"steem_balance" : float(self.session['balance'].replace('STEEM', '')),
		"sbd_balance" : float(self.session['sbd_balance'].replace('SBD', '')),
		"vests" : float(self.session['vesting_shares'].replace('VESTS', '')),
		"delegated_vests" : float(self.session['received_vesting_shares'].replace('VESTS', '')) - float(self.session['delegated_vesting_shares'].replace('VESTS', '')),
		"delegated_vesting_shares" : float(self.session['delegated_vesting_shares'].replace('VESTS', '')),
		"received_vesting_shares" : float(self.session['received_vesting_shares'].replace('VESTS', '')),
		"voting_power" : float(self.session['voting_power'] / 100)
		}

		self.wallet['acc_value'] = self.calculate_estimated_acc_value()
		self.wallet['upvote'] = self.calculate_estimated_upvote()
		self.wallet['delegations'] = self.calculate_steem_power()['delegations']
		self.wallet['sp_balance'] = self.calculate_steem_power()['sp_balance']

	# Is used to calculate steem power of a given user based on their vests.
	def calculate_steem_power(self):

		post = '{"id":1,"jsonrpc":"2.0","method":"get_dynamic_global_properties", "params": []}'
		response = session_post('https://api.steemit.com', post)
		data = json.loads(response.text)
		data = data['result']

		total_vesting_fund_steem = float(data['total_vesting_fund_steem'].replace('STEEM', ''))
		total_vesting_shares = float(data['total_vesting_shares'].replace('VESTS', ''))

		sp_dict = {
		"sp_balance" : round(total_vesting_fund_steem * (self.wallet['vests']/total_vesting_shares), 2),
		"delegations" : round(total_vesting_fund_steem * (self.wallet['delegated_vests']/total_vesting_shares), 2)
		}

		return sp_dict

	# Is used to calculate the estimated account value of a given user.
	def calculate_estimated_acc_value(self):
		response = requests.get("https://api.coinmarketcap.com/v1/ticker/?limit=500")
		data = json.loads(response.text)
		for x in data:
			if x['id'] == "steem":
				steem_price = x['price_usd']
				if float(steem_price) > 1:
					steem_price = round(float(steem_price),2)
			elif x['id'] == "steem-dollars":
				sbd_price = x['price_usd']
				if float(sbd_price) > 1:
					sbd_price = round(float(sbd_price),2)

		outcome = round(((self.calculate_steem_power()['sp_balance'] + self.wallet['steem_balance']) * steem_price ) + (self.wallet['sbd_balance'] * sbd_price), 2)

		return str(outcome) + " USD"

	# Is used to calculate the estimated upvote of a given user.
	def calculate_estimated_upvote(self):
		reward_fund = s.get_reward_fund()
		sbd_median_price = get_current_median_history_price()
		vests = float(self.session['vesting_shares'].replace('VESTS', '')) + float(self.session['received_vesting_shares'].replace('VESTS', '')) - float(self.session['delegated_vesting_shares'].replace('VESTS', ''))
		vestingShares = int(vests * 1e6);
		rshares = 0.02 * vestingShares
		estimated_upvote = rshares / float(reward_fund['recent_claims']) * float(reward_fund['reward_balance'].replace('STEEM', '')) * sbd_median_price
			
		return estimated_upvote

#################################################
# This is where Alexa unrelated functions begin #
#################################################

def session_post(url, post):
	headers = {
		'User-Agent': 'Steem-Assistant'
	}

	return session.post(url, data = post, headers = headers, timeout = 30)

# Gets median history price of SBD from the steem blockchain. Necessary for calculating relation between SP and vests.
def get_current_median_history_price():
	price = 0.0

	data = '{"id":1,"jsonrpc":"2.0","method":"get_current_median_history_price"}'
	response = session_post('https://api.steemit.com', data)
	data = json.loads(response.text)
	
	if 'result' in data:
		price = float(data['result']['base'].replace('SBD', ''))		
	else:
		raise Exception('Couldnt get the SBD price!')
	
	return price

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

###############################################
# This is where alexa related functions begin #
###############################################

@app.route('/')
def homepage():
	return "Placeholder page for Steem-Assistant"

# This is what alexa will say if you ask echo to "Use Steem Assistant"
@ask.launch
def start_skill():
	welcome_msg = 'Welcome to Steem Assistant, what can I assist you with?'

	return question(welcome_msg)

# Reads out the information about the user's wallet
@ask.intent("WalletIntent")
def check_wallet():
	user = SteemUser(nickname)
	steem_balance = str(user.wallet['steem_balance']) + " STEEM"
	sbd_balance = str(user.wallet['sbd_balance']) + " Steem Dollars"
	sp_balance = str(user.wallet['sp_balance']) + " Steem Power"	
	acc_value = str(user.wallet['acc_value'])

	response = "Currently, in your wallet you've got: %s, %s, %s. Your estimated account value is %s." % (steem_balance, sbd_balance, sp_balance, acc_value)
	return statement(response)

# Reads out a specific thing from the user's wallet
@ask.intent("SpecificWalletIntent")
def check_one_from_wallet(item):
	user = SteemUser(nickname)

	if item == "steem":
		name = "steem_balance"
		response_name = "steem"
	elif item == "sbd" or item == "steem dollars":
		name = "sbd_balance"
		response_name = "steem dollars"
	elif item == "sp" or item == "steem power":
		name = "sp_balance"
		response_name = "steem power"
	elif item == "voting power":
		name = "voting_power"
		response_name = "voting power"
	elif item == "delegations":
		name = "delegations"
		response_name = "steem power in delegations"
	elif item == "account value":
		response = "Your estimated account value is equal to %s USD." % (user.wallet["acc_value"])
		return statement(reponse)
	elif item == "upvote":
		response = "Your estimated upvote is equal to %s Steem Dollars." % (round(user.wallet["upvote"],2))
		return statement(response)
	else:
		 name, response_name = item, item


	response = "You currently have %s %s ." %(user.wallet[name], response_name)
	return statement(response)


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
			if float(price) > 1:
				price = round(float(price),2)
			name = x['name']
			change = x['percent_change_24h']
			rank = x['rank']
			if rank[-1] == "1":
				rank = str(rank+"st place ")
			elif rank[-1] == "2":
				rank = str(rank+"nd place ")
			elif rank[-1] == "3":
				rank = str(rank+"rd place ")
			else:
				rank = str(rank+"th place ")
			available = True
			break
		else:
			available = False
	if available:	
		response = "The current price of %s is %s USD and is ranked at %s. In the last 24h it's price has changed by %s percent." %(name, price, rank, change)
	else:
		response = "I don't think I got the name correct. Try to give me the symbol of the coin rather than it's name to see if that works."

	return statement(response)

if __name__ == '__main__':
	app.run(port=8000)
