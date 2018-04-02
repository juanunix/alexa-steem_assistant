import urllib.parse
from flask import Flask, redirect, request, url_for
import requests
from requests.exceptions import RequestException

app = Flask(__name__)
app.secret_key = "app_secret_key_here"


@app.route('/login')
def login_steemit():
    query_string = urllib.parse.urlencode({
        'client_id': 'app_name_here',
        'redirect_uri': url_for('callback', _external=True),
        'scope': 'login',
    })
    url = "https://v2.steemconnect.com/oauth2/authorize?{qs}".format(qs=query_string)
    return redirect(url, code=302)


@app.route('/callback', methods=['GET'])
def callback():
    access_token = request.args.get('access_token')

    headers = {
        'Authorization': access_token,
        'Accept': 'application/json',
    }
    error = None
    try:
        response = requests.get("https://v2.steemconnect.com/api/me", headers=headers, timeout=10)
    except RequestException as ex:
        error = str(ex)

    status = response.status_code
    if status != 200:
        error = "We got {} response from server.".format(status)

    try:
        response_json = response.json()
    except ValueError:
        error = "We got invalid response from server."

    if error:
        return error

    return "<h2>Congrats</h2><h4>Welcome: {}</h4><h4>Account info:</h4><pre>{}</pre>".format(
        response_json.get('user'), response_json.get('account'))


if __name__ == 'main':
    app.run(debug=True)
