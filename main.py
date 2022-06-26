from flask import Flask, render_template, redirect, url_for
from requests import Session
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import json
import smtplib
import ssl

# APP SETUP
app = Flask(__name__)
Bootstrap(app)
app.config['SECRET_KEY'] = 'APP_SECRET_KEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crypto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Crypto Coin Data
class Crypto:
    def __init__(self, id, name, price, change):
        self.id = id
        self.name = name
        self.price = price
        self.change = change

# WTForm
class AddCrypto(FlaskForm):
    name = StringField("Enter name of crypto: ", validators=[DataRequired()])
    submit = SubmitField("Add")

# DATABASE TABLE
class CryptoCoin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    # week_lowest = db.Column(db.Float, nullable=False)

db.create_all()


# CONSTANTS
CMC_API_KEY = 'YOUR COIN_MARKET_CAP API KEY'
url = 'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest'
USERNAME = 'YOUR_EMAIL'
PASSWORD = 'YOUR_PASSWORD'


def get_api_params():
    '''Get the names of cryptocurrencies stored in our database.'''
    coins = CryptoCoin.query.all()
    slugs = ''
    for coin in coins:
        slugs = slugs + coin.name.lower() + ','
    return slugs[:-1]
    


def get_crypto_prices(slugs):
    '''Get the real-time prices of the added crypto coins.'''
    parameters = {
    'slug': slugs
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
    }
    session = Session()
    session.headers.update(headers)
    response = session.get(url, params=parameters)
    data = json.loads(response.text)

    crypto_list = []
    coins = data['data']

    for curr in coins.items():
        curr_id = curr[0]
        curr_name = data['data'][f'{curr_id}']['name']
        curr_price = "{:.2f}".format(data['data'][f'{curr_id}']['quote']['USD']['price'])
        curr_change = "{:.2f}".format(data['data'][f'{curr_id}']['quote']['USD']['percent_change_24h'])
        crypto_coin = Crypto(curr_id, curr_name, curr_price, curr_change)
        crypto_list.append(crypto_coin)

    return crypto_list



@app.route('/')
def home():
    slugs = get_api_params()
    currencies = get_crypto_prices(slugs)

    message = ''

    for coin in currencies:
        if coin.change[0] == '-':
            float_value = float(coin.change)
            if float_value <= -3:
                message += f'Price of {coin.name} is up by {float_value * -1}% \n'
        else:
            float_value = float(coin.change)
            if float_value >=3:
                message += f'Price of {coin.name} is down by {float_value}% \n'

    if message != '':
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as connection:
            connection.login(user=USERNAME, password='YOUR APP PASSWORD')
            connection.sendmail(
                from_addr=USERNAME,
                to_addrs='TO ADDRESS',
                msg=f"Subject: Alert! Crypto Price Update! \n\n {message}"
            )

    return render_template('index.html', currencies=currencies)


@app.route('/add', methods=['POST', 'GET'])
def add_crypto():
    form = AddCrypto()
    if form.validate_on_submit():
        coin_name = form.name.data.lower()
        new_coin_data = get_crypto_prices(coin_name)
        new_coin = CryptoCoin(
            id = new_coin_data[0].id,
            name = new_coin_data[0].name
        )
        db.session.add(new_coin)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('add.html', form=form)


@app.route('/delete/<int:coin_id>')
def delete(coin_id):
    coin_to_delete = CryptoCoin.query.get(coin_id)
    db.session.delete(coin_to_delete)
    db.session.commit()
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run()
