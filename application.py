from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp

from helpers import *
from funcs import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.route("/")
@login_required
def index():
    
    if "user_id" in session:
        return redirect("portfolio")
        
    return redirect("login")
    
@app.route("/portfolio")
@login_required
def porfolio():
    stocks = get_user_stocks()
    total = 0
    #get and set current price for stocks in portfolio
    for stock in stocks:
        if stock["amount"] <= 0:
            remove_empty_stocks()
            return redirect(url_for("index"))
        price = lookup(stock["symbol"])
        stock["currentprice"] = price["price"]
        price = stock["currentprice"] * stock["amount"]
        total += price
    #get cash balance and add to total stock values
    balance = get_cash_balance()
    length = len(balance)
    if length == 0:
        cash = 20000
    else:
        cash = balance[0]["cash"]

    total += cash
    
    return render_template("index.html", stocks=stocks, balance=cash, total_value=total)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    
    if request.method == "POST":
        #get form data
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        #validate data
        if symbol == '' or symbol.isalpha() == False:
            return apology("Please enter a valid symbol")
        elif shares == '':
            return apology("Please enter number of shares to buy")
        #get a quote
        quote = lookup(symbol)
        if quote == None or quote == '':
            return apology("Unable to locate Symbol")
                
        #check if cash is available
        get_cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
        cash = get_cash
        total = float(shares) * quote["price"]
        if cash[0]["cash"] < total:
            return apology("You do not have enough cash")
        elif cash[0]["cash"] >= total:
            #subtract price total from cash
            cash_minus_value(total)
            db.execute("INSERT INTO portfolio(amount, name, owner, symbol, purchaseprice, totalvalue) VALUES (:amount, :name, :owner, :symbol, :purchaseprice, :total)", amount=shares, name=quote["name"], owner=session["user_id"], symbol=quote["symbol"], purchaseprice=quote["price"], total=total)
            
            insert_history("Buy", symbol, quote["price"], shares)
            
        return redirect(url_for("index"))
    cash_balance = get_cash_balance()
    
    #if not a post then get and show buy form
    return render_template("buy.html", cash=cash_balance[0]["cash"])

@app.route("/history")
@login_required
def history():
    user_history = get_history()
    
    """Show history of transactions."""
    return render_template("history.html", history=user_history)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session['user_id'] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        #retreive symbol
        symbol = request.form.get("symbol")
        #validate symbol
        if symbol == '':
            return apology("Insert a symbol")
        #lookup symbol
        quote = lookup(symbol)
        """Get stock quote."""
        if quote == None or quote == '':
            return apology("Unable to locate Symbol")
        #show quote
        return render_template("quoted.html", quote=quote)
    #get requests to form
    return render_template("quote.html")
    

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    if request.method == "POST":
        #check password for validity
        user_name = request.form.get("username")
        user_pass = request.form.get("password")
        #check username for validity
        if user_name == db.execute("SELECT * FROM users WHERE username = :username", username=user_name):
            return apology("A user with that username already exists!")
        elif user_name == '':
            return apology("Must include a username!")
        if user_pass == '':
            return apology("Must provide password!")
        elif user_pass != request.form.get("confirmpassword"):
            return apology("Passwords must match!")
        else:
            hash_pw = pwd_context.hash(user_pass)
        #insert new user into db
        cash = 20000
        db.execute("INSERT INTO users(username, hash, cash) VALUES (:username, :hash, :cash)", username=user_name, hash=hash_pw, cash=cash)
        
        #save user to session
        session['user_id'] = user_name
        

        #redirect logged in user to root path
        return redirect(url_for("index"))
    
    
    #display form if not logged in
    return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
        
    #get stocks
    stocks = get_user_stocks()

    
    #if post method
    if request.method == "POST":
        total = 0
        #get current prices
        for stock in stocks:
            price = lookup(stock["symbol"])
            stock["currentprice"] = price["price"]
            price = stock["currentprice"] * stock["amount"]
            total += price

            
        #get symbol from form
        stock_to_sell = request.form.get('select')
        #get that stocks current value
        get_stock_to_sell_value = lookup(stock_to_sell)
        sell_price = get_stock_to_sell_value["price"]
        #get the # shares
        current_symbol = get_stock_to_sell_value["symbol"]
        # get_shares = amount_shares(current_symbol)
        get_shares = request.form.get('shares')
        share_amount = get_shares
        test = amount_shares(current_symbol)
        if test[0]["amount"] < int(share_amount):
            return apology("You selected more shares than you own, try again")
        #calculate # shares to sell times current price
        sell_value = float(share_amount) * float(sell_price)

        print(sell_value)

        #retreive purchaseprice from db
        get_purchase_price = db.execute("SELECT purchaseprice FROM portfolio WHERE owner=:id AND symbol=:symbol", id=session['user_id'], symbol=stock_to_sell)
        #get purchase price of stock to sell
        purchase_price = get_purchase_price[0]["purchaseprice"]
        #calculate total purchase value
        purchased_value = float(purchase_price) * float(share_amount)
        
        print(purchased_value)
        
        #add to cash if gain
        earned_value = sell_value - purchased_value
        
        
        print(earned_value)
        
        
        db.execute("UPDATE users SET cash = cash + :sold WHERE id = :id", sold=earned_value, id=session['user_id'])
  
        
        
        db.execute("UPDATE portfolio SET amount = amount - :shares WHERE symbol=:symbol", shares=get_shares, symbol=stock_to_sell)
        
        insert_history("Sell", current_symbol, sell_price, get_shares)

        
        return redirect(url_for("index"))
    
    #if get method
    """Sell shares of stock."""
    return render_template("sell.html", stocks=stocks)
    
@app.route("/resetpw", methods=["GET", "POST"])
def resetpw():
    if request.method == "POST":
        
        #check password for validity
        user_name = request.form.get("username")
        user_pass = request.form.get("password")
        #check username for validity
        try:
            user = db.execute("SELECT * FROM users WHERE username = :username", username=user_name)
        except:
            return apology("User does not exist")
        
        if user_name == '':
            return apology("Must include a username!")
        if user_pass == '':
            return apology("Must provide password!")
        elif user_pass != request.form.get("confirmpassword"):
            return apology("Passwords must match!")
        
        hash_pw = pwd_context.hash(user_pass)

        #save user to session
        # session['user_id'] = user_name
        
        db.execute("UPDATE users SET hash = :hash_pw WHERE username = :username", username=user_name, hash_pw=hash_pw)
        
        
        return redirect(url_for('index'))
        
    
    return render_template("resetpw.html")