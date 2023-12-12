import datetime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from functools import wraps

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///cdz.db")

def php(value):
    """Format value as Php."""
    try:
        return f"₱{abs(value):,.2f}"
    except:
        return (value)

def dec(value):
    try:
        return f"{abs(value):,.2f}"
    except:
        return (value)

def vp(value):
    """Format value as VP."""
    try:
        return f"{int(value)} VP"
    except:
        return (value)

# Require login on admin functions
def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

# Custom filter
app.jinja_env.filters["php"] = php
app.jinja_env.filters["dec"] = dec
app.jinja_env.filters["vp"] = vp

@app.route("/")
def home():
    try:
        user_id = session["user_id"]
        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]
        return render_template("home.html", username = username)
    except:
        return render_template("home.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        session.clear()

        if not username:
            flash("Enter username!")
            return redirect("/admin")

        if not password:
            flash("Enter password!")
            return redirect("/admin")

        account = db.execute("SELECT * FROM users WHERE username = ?", username)

        if len(account) != 1 or not check_password_hash(account[0]["hash"], password):
            flash("Invalid username and/or password!")
            return redirect("/admin")

        session["user_id"] = account[0]["id"]

        return redirect("/")

    else:
        return render_template("admin.html")


@app.route("/logout")
@login_required
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to home
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        key = request.form.get("key")

        if not username:
            flash("Enter username!")
            return redirect("/register")

        if not password:
            flash("Enter password!")
            return redirect("/register")

        if not confirmation:
            flash("Must confirm password!")
            return redirect("/register")

        if not key:
            flash("Key must be provided!")
            return redirect("/register")

        if password != confirmation:
            flash("Password does not match!")
            return redirect("/register")

        if key != "123":
            flash("Incorrect Key!")
            return redirect("/register")

        hash = generate_password_hash(password)

        try:
            new_user = db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
        except:
            flash("Username already taken!")
            return redirect("/register")

        session["user_id"] = new_user

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/stocks", methods=["GET", "POST"])
@login_required
def stocks():
    if request.method == "POST":
        amount = request.form.get("amount")
        stock_id = request.form.get("stock_id")
        user_id = session["user_id"]
        date = datetime.datetime.now()
        transaction_type = "Load"

        if not stock_id:
            flash("Select sim card!")
            return redirect("/stocks")

        if not amount:
            flash("Enter amount!")
            return redirect("/stocks")

        current_bal_db = db.execute("SELECT balance FROM stocks WHERE user_id=? AND stock_id=?", user_id, stock_id)
        current_bal = current_bal_db[0]["balance"]

        amount_int = int(amount)

        new_bal = current_bal + amount_int

        db.execute("UPDATE stocks SET balance=? WHERE user_id=? AND stock_id=?", new_bal, user_id, stock_id)

        db.execute("INSERT INTO history (stock_id, load_amount, transaction_type, date) VALUES(?, ?, ?, ?)", stock_id, amount, transaction_type, date)

        flash("Added successfully!")
        return redirect("/stocks")

    else:
        toggle = request.args.get("toggle")

        user_id = session["user_id"]

        sim_user = db.execute("SELECT sim_name, stock_id FROM stocks WHERE user_id = ?", user_id)

        stocks = db.execute("SELECT sim_name, network, sim_number, stock_id, balance FROM stocks WHERE user_id=? ORDER BY balance DESC", user_id)

        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]

        total_bal_db = db.execute("SELECT SUM(balance) FROM stocks WHERE user_id = ?", user_id)

        total_bal = total_bal_db[0]["SUM(balance)"]

        return render_template("stocks.html", toggle = toggle, database = stocks, sim_names = sim_user, username = username, total_bal = total_bal)


@app.route("/deleteStock")
def deleteStock():
    stock_id = request.args.get("stock_id")

    db.execute("DELETE FROM stocks WHERE stock_id = ?", stock_id)
    return redirect("/stocks?toggle=edit")

@app.route("/clearAllStock")
def clearAllStock():
    user_id = session["user_id"]

    db.execute("DELETE FROM stocks WHERE user_id = ?", user_id)
    return redirect("/stocks")

@app.route("/history")
@login_required
def history():
    toggle = request.args.get("toggle")

    user_id = session["user_id"]

    # Filter the transactions
    filter = request.args.get("filter")
    search = request.args.get("search")

    if filter == "type":
        filter_by = db.execute("SELECT sim_name, load_amount, transaction_type, date, id, stocks.stock_id FROM history JOIN stocks ON stocks.stock_id = history.stock_id WHERE user_id=? AND transaction_type LIKE ?", user_id, search + "%")
    elif filter == "sim":
        filter_by = db.execute("SELECT sim_name, load_amount, transaction_type, date, id, stocks.stock_id FROM history JOIN stocks ON stocks.stock_id = history.stock_id WHERE user_id=? AND sim_name LIKE ?", user_id, search + "%")
    elif filter == "date":
        filter_by = db.execute("SELECT sim_name, load_amount, transaction_type, date, id, stocks.stock_id FROM history JOIN stocks ON stocks.stock_id = history.stock_id WHERE user_id=? AND date LIKE ?", user_id, search + "%")
    else:
        filter_by = db.execute("SELECT sim_name, load_amount, transaction_type, date, id, stocks.stock_id FROM history JOIN stocks ON stocks.stock_id = history.stock_id WHERE user_id=? ORDER BY date DESC", user_id)

    username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)

    username = username_db[0]["username"]

    return render_template("history.html", database = filter_by, username = username, toggle = toggle, filter = filter, search = search)

@app.route("/undoHistory")
def undoHistory():
    id = request.args.get("id")
    stock_id = request.args.get("stock_id")

    load_amount_db = db.execute("SELECT load_amount FROM history WHERE id = ?", id)
    load_amount = load_amount_db[0]["load_amount"]

    user_id = session["user_id"]
    current_bal_db = db.execute("SELECT balance FROM stocks WHERE user_id=? AND stock_id=?", user_id, stock_id)
    current_bal = current_bal_db[0]["balance"]

    transaction_type_db = db.execute("SELECT transaction_type FROM history WHERE id = ?", id)
    transaction_type = transaction_type_db[0]["transaction_type"]

    if transaction_type == "Load":
        new_bal = current_bal - load_amount
    else:
        new_bal = current_bal + load_amount

        try:
            date_db = db.execute("SELECT date FROM history WHERE id = ?", id)
            date = date_db[0]["date"]

            transaction_id_db = db.execute("SELECT transaction_id FROM transactions WHERE stock_id = ? AND transaction_date =?", stock_id, date)
            transaction_id = transaction_id_db[0]["transaction_id"]

            db.execute("DELETE FROM transactions WHERE transaction_id = ?", transaction_id)
        except:
            pass

    network_db = db.execute("SELECT network FROM stocks WHERE stock_id = ?", stock_id)
    network = network_db[0]["network"]

    if network != "N/A":
        db.execute("UPDATE stocks SET balance=? WHERE user_id=? AND stock_id=?", new_bal, user_id, stock_id)

    db.execute("DELETE FROM history WHERE id = ?", id)

    return redirect("/history?filter={{ filter }}&search={{ search }}&toggle=edit")

@app.route("/deleteHistory")
def deleteHistory():
    id = request.args.get("id")

    db.execute("DELETE FROM history WHERE id = ?", id)
    return redirect("/history?filter={{ filter }}&search={{ search }}&toggle=edit")

@app.route("/clearAllHistory")
def clearAllHistory():
    user_id = session["user_id"]

    db.execute("DELETE FROM history WHERE id IN (SELECT id FROM history JOIN stocks ON stocks.stock_id = history.stock_id WHERE user_id=?)", user_id)
    return redirect("/history")


@app.route("/addSim", methods=["GET", "POST"])
@login_required
def addSim():
    if request.method == "POST":
        sim_card_name = request.form.get("sim_card_name")
        sim_number = request.form.get("number")
        balance = request.form.get("balance")
        network = request.form.get("network")

        if not network:
            flash("Enter sim card network!")
            return redirect("/addSim")

        if not sim_card_name:
            flash("Enter Sim Card Name!")
            return redirect("/addSim")

        if not sim_number:
            flash("Enter Sim Card Name!")
            return redirect("/addSim")

        if not balance:
            flash("Balance cannot be blank!")
            return redirect("/addSim")

        float_balance = float(balance)

        if float_balance < 0:
            flash("Balance cannot be negative number!")
            return redirect("/addSim")

        date = datetime.datetime.now()
        user_id = session["user_id"]

        try:
            db.execute("INSERT INTO stocks (user_id, network, sim_name, sim_number, balance, date_added) VALUES (?, ?, ?, ?, ?, ?)", user_id, network, sim_card_name, sim_number, balance, date)
        except:
            flash("Sim number already exist!")
            return redirect("/addSim")

        flash("Added Sim Sucessfully!")
        return redirect("/stocks")

    else:
        user_id = session["user_id"]
        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]
        return render_template("add_sim.html", username = username)

@app.route("/transactions", methods=["GET", "POST"])
@login_required
def transactions():
    if request.method == "POST":
        top_up_type = request.form.get("top_up")
        stock_id = request.form.get("stock_id")
        transaction_amount = request.form.get("amount")
        load_amount = request.form.get("load")
        discount = request.form.get("discount")

        if not top_up_type:
            flash("Select game credit!")
            return redirect("/transactions")

        if not stock_id:
            flash("Select sim card!")
            return redirect("/transactions")

        if not transaction_amount:
            flash("Enter amount!")
            return redirect("/transactions")

        if not load_amount:
            flash("Enter load!")
            return redirect("/transactions")

        if not discount:
            flash("Enter discount!")
            return redirect("/transactions")

        int_transaction_amount = int(transaction_amount)
        int_load_amount = int(load_amount)
        int_discount = int(discount)

        user_id = session["user_id"]
        current_bal_db = db.execute("SELECT balance FROM stocks WHERE user_id=? AND stock_id=?", user_id, stock_id)
        current_bal = current_bal_db[0]["balance"]

        network_db = db.execute("SELECT network FROM stocks WHERE stock_id=?", stock_id)
        network = network_db[0]["network"]

        if network != "N/A":
            if int_load_amount > current_bal:
                flash("Not enough stocks!")
                return redirect("/transactions")

        # Compute Profit
        profit = int_transaction_amount - (int_load_amount * (1 - (int_discount * .01) ))

        # Add the values into transaction database

        date = datetime.datetime.now()

        db.execute("INSERT INTO transactions (stock_id, top_up_type, transaction_amount, transaction_load, discount, profit, transaction_date) VALUES (?, ?, ?, ?, ?, ?, ?)", stock_id, top_up_type, int_transaction_amount, int_load_amount, int_discount, profit, date)

        # Add the values into history
        if network != "N/A":
            transaction_type = "Top up"

            db.execute("INSERT INTO history (stock_id, load_amount, transaction_type, date) VALUES(?, ?, ?, ?)", stock_id, load_amount, transaction_type, date)

        # Update stock balance
        if network == "N/A":
            flash("Top up successful!")
            return redirect("/transactions")

        else:
            new_bal = current_bal - int_load_amount

            db.execute("UPDATE stocks SET balance=? WHERE user_id=? AND stock_id=?", new_bal, user_id, stock_id)

            flash("Top up successful!")
            return redirect("/transactions")

    else:
        toggle = request.args.get("toggle")

        user_id = session["user_id"]
        sim_user = db.execute("SELECT sim_name, stock_id, balance FROM stocks WHERE user_id = ?", user_id)

        # Filter the transactions
        filter = request.args.get("filter")
        search = request.args.get("search")

        if filter == "game":
            filter_by = db.execute("SELECT top_up_type, sim_name, transaction_amount, transaction_load, discount, profit, transaction_date, transaction_id, stocks.stock_id FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND top_up_type LIKE ?", user_id, search + "%")
        elif filter == "sim":
            filter_by = db.execute("SELECT top_up_type, sim_name, transaction_amount, transaction_load, discount, profit, transaction_date, transaction_id, stocks.stock_id FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND sim_name LIKE ?", user_id, search + "%")
        elif filter == "date":
            filter_by = db.execute("SELECT top_up_type, sim_name, transaction_amount, transaction_load, discount, profit, transaction_date, transaction_id, stocks.stock_id FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND transaction_date LIKE ?", user_id, search + "%")
        else:
            filter_by = db.execute("SELECT top_up_type, sim_name, transaction_amount, transaction_load, discount, profit, transaction_date, transaction_id, stocks.stock_id FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? ORDER BY transaction_date DESC", user_id)

        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)

        username = username_db[0]["username"]

        return render_template("transactions.html", database = filter_by, sim_names = sim_user, username = username, toggle = toggle, filter = filter, search = search)

@app.route("/undoTransaction")
def undoTransaction():
    transaction_id = request.args.get("transaction_id")
    stock_id = request.args.get("stock_id")

    network_db = db.execute("SELECT network FROM stocks WHERE stock_id = ?", stock_id)
    network = network_db[0]["network"]

    if network != "N/A":
        user_id = session["user_id"]
        current_bal_db = db.execute("SELECT balance FROM stocks WHERE user_id=? AND stock_id=?", user_id, stock_id)
        current_bal = current_bal_db[0]["balance"]

        transaction_load_db = db.execute("SELECT transaction_load FROM transactions WHERE transaction_id = ?", transaction_id)
        transaction_load = transaction_load_db[0]["transaction_load"]

        new_bal = current_bal + transaction_load

        db.execute("UPDATE stocks SET balance=? WHERE user_id=? AND stock_id=?", new_bal, user_id, stock_id)

    try:
        transaction_date_db = db.execute("SELECT transaction_date FROM transactions WHERE transaction_id = ?", transaction_id)
        transaction_date = transaction_date_db[0]["transaction_date"]
        id_db = db.execute("SELECT id FROM history WHERE stock_id = ? AND date =?", stock_id, transaction_date)
        id = id_db[0]["id"]

        db.execute("DELETE FROM history WHERE id = ?", id)
        db.execute("DELETE FROM transactions WHERE transaction_id = ?", transaction_id)

        return redirect("/transactions?filter={{ filter }}&search={{ search }}&toggle=edit")
    except:
        pass

    return redirect("/transactions?filter={{ filter }}&search={{ search }}&toggle=edit")

@app.route("/deleteTransaction")
def deleteTransaction():
    transaction_id = request.args.get("transaction_id")

    db.execute("DELETE FROM transactions WHERE transaction_id = ?", transaction_id)
    return redirect("/transactions?filter={{ filter }}&search={{ search }}&toggle=edit")

@app.route("/clearAllTransactions")
def clearAllTransactions():
    user_id = session["user_id"]

    db.execute("DELETE FROM transactions WHERE transaction_id IN (SELECT transaction_id FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=?)", user_id)
    return redirect("/transactions")

@app.route("/analytics")
@login_required
def analytics():
        # Compute for the Total Profit
        user_id = session["user_id"]

        filter_from = request.args.get("filter_from")
        filter_to = request.args.get("filter_to")

        if filter_from and not filter_to:
            flash("Enter 'To' date!")
        if filter_to and not filter_from:
            flash("Enter 'From' date!")

        if filter_from and filter_to:

            profit_date = f"From: {filter_from} To: {filter_to}"

            total_profit_db = db.execute("SELECT SUM(profit) FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND transaction_date BETWEEN ? AND ?", user_id, filter_from + "%", filter_to + "%")
            order_count_db = db.execute("SELECT COUNT(transaction_id) FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND transaction_date BETWEEN ? AND ?", user_id, filter_from + "%", filter_to + "%")
        else:
            profit_date = "This month."
            current_date = datetime.datetime.now()
            current_year = current_date.year
            current_month = current_date.month

            date = f"{current_year}-{current_month}"

            total_profit_db = db.execute("SELECT SUM(profit) FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND transaction_date LIKE ?", user_id, date + "%")
            order_count_db = db.execute("SELECT COUNT(transaction_id) FROM transactions JOIN stocks ON stocks.stock_id = transactions.stock_id WHERE user_id=? AND transaction_date LIKE ?", user_id, date + "%")

        total_profit = total_profit_db[0]["SUM(profit)"]
        order_count = order_count_db[0]["COUNT(transaction_id)"]

        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)

        username = username_db[0]["username"]

        return render_template("analytics.html", total_profit = total_profit, order_count = order_count, profit_date = profit_date, username = username)


@app.route("/prices")
def prices():
    valorant = db.execute("SELECT * FROM valorant_pricelist")

    genshin = db.execute("SELECT * FROM genshin_pricelist")

    mlbb = db.execute("SELECT * FROM mlbb_pricelist")

    wild_rift = db.execute("SELECT * FROM wild_rift_pricelist")

    riot_points = db.execute("SELECT * FROM riot_points_pricelist")

    garena_shells = db.execute("SELECT * FROM garena_shells_pricelist")

    try:
        user_id = session["user_id"]
        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]
        return render_template("prices.html", username = username, valorant=valorant, genshin = genshin, mlbb = mlbb, wild_rift = wild_rift, riot_points = riot_points, garena_shells = garena_shells )
    except:
        return render_template("prices.html", valorant=valorant, genshin = genshin, mlbb = mlbb, wild_rift = wild_rift, riot_points = riot_points, garena_shells = garena_shells)



@app.route("/order")
def order():

    try:
        user_id = session["user_id"]
        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]
        return render_template("order.html", username = username)
    except:
        return render_template("order.html")


@app.route("/about")
def about():

    try:
        user_id = session["user_id"]
        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]
        return render_template("about.html", username = username)
    except:
        return render_template("about.html")

@app.route("/calculator")
def calculator():
    amount = request.args.get("amount")

    vp_5800 = 0
    vp_2850 = 0
    vp_1650 = 0
    vp_790 = 0
    vp_380 = 0
    vp_125 = 0

    load =0

    reco_1 = 0
    reco_2 = 0
    price_1 = 0
    price_2 = 0

    if not amount:
        base_amount = "None"
        price = "None"

    else:
        base_amount = int(amount)
        current_amount = int(amount)
        vp_amount = 0
        price = 0

        if base_amount < 125:
                vp_125 += 1

        while current_amount >= 5800:
            current_amount -= 5800
            vp_5800 += 1

        while current_amount >= 2850:
            current_amount -= 2850
            vp_2850 += 1

        while current_amount >= 1650:
            current_amount -= 1650
            vp_1650 += 1

        while current_amount >= 790:
            current_amount -= 790
            vp_790 += 1

        while current_amount >= 380:
            current_amount -= 380
            vp_380 += 1

        while current_amount >= 125:
            current_amount -= 125
            vp_125 += 1

        price = (1840 * vp_5800) + (920 * vp_2850) + (550 * vp_1650) + (275 * vp_790) +  (140 * vp_380) + (50 * vp_125)
        load = (2000 * vp_5800) + (1000 * vp_2850) + (600 * vp_1650) + (300 * vp_790) +  (150 * vp_380) + (50 * vp_125)
        vp_amount = (5800 * vp_5800) + (2850 * vp_2850) + (1650 * vp_1650) + (790 * vp_790) +  (380 * vp_380) + (125 * vp_125)

        if base_amount == vp_amount:
            if vp_amount < 5800 and price >= 1840:
                reco_1 = 5800
                price_1 = 1840

            if vp_amount < 2850 and price >= 920:
                reco_1 = 2850
                price_1 = 920

            if vp_amount < 1650 and price >= 550:
                reco_1 = 1650
                price_1 = 550

            if vp_amount < 790 and price >= 275:
                reco_1 = 790
                price_1 = 275

            if vp_amount < 380 and price >= 140:
                reco_1 = 380
                price_1 = 140

        elif base_amount != vp_amount:
            reco_2 = vp_amount
            price_2 = price

            price = "No exact amount."

            vp_5800 = 0
            vp_2850 = 0
            vp_1650 = 0
            vp_790 = 0
            vp_380 = 0
            vp_125 = 0

            vp_amount = 0

            current_amount = int(amount)

            while current_amount >= 5800:
                current_amount -= 5800
                vp_5800 += 1

            while 5800 > current_amount > 5700:
                current_amount = 5800
                current_amount -= 5800
                vp_5800 += 1

            while current_amount >= 2850:
                current_amount -= 2850
                vp_2850 += 1

            while 2850 > current_amount > 2565:
                current_amount = 2850
                current_amount -= 2850
                vp_2850 += 1

            while current_amount >= 1650:
                current_amount -= 1650
                vp_1650 += 1

            while 1650 > current_amount > 1420:
                current_amount = 1650
                current_amount -= 1650
                vp_1650 += 1

            while current_amount >= 790:
                current_amount -= 790
                vp_790 += 1

            while 790 > current_amount > 630:
                current_amount = 790
                current_amount -= 790
                vp_790 += 1

            while current_amount >= 380:
                current_amount -= 380
                vp_380 += 1

            while 380 > current_amount > 250:
                current_amount = 380
                current_amount -= 380
                vp_380 += 1

            while current_amount >= 125:
                current_amount -= 125
                vp_125 += 1

            while 125 > current_amount > 0:
                current_amount = 125
                current_amount -= 125
                vp_125 += 1


            reco_1 = (5800 * vp_5800) + (2850 * vp_2850) + (1650 * vp_1650) + (790 * vp_790) +  (380 * vp_380) + (125 * vp_125)
            price_1 = (1840 * vp_5800) + (920 * vp_2850) + (550 * vp_1650) + (275 * vp_790) +  (140 * vp_380) + (50 * vp_125)

    try:
        user_id = session["user_id"]
        username_db = db.execute("SELECT username FROM users WHERE id = ?", user_id)
        username = username_db[0]["username"]
        return render_template("calculator.html",
                            username = username,
                            base_amount = base_amount,
                            price = price,
                            reco_1 = reco_1,
                            reco_2 = reco_2,
                            price_1 = price_1,
                            price_2 = price_2,
                            vp_5800 = vp_5800,
                            vp_2850 = vp_2850,
                            vp_1650 = vp_1650,
                            vp_790 = vp_790,
                            vp_380 = vp_380,
                            vp_125 = vp_125,
                            load = load)
    except:
        return render_template("calculator.html",
                                base_amount = base_amount,
                                price = price,
                                reco_1 = reco_1,
                                reco_2 = reco_2,
                                price_1 = price_1,
                                price_2 = price_2,
                                vp_5800 = vp_5800,
                                vp_2850 = vp_2850,
                                vp_1650 = vp_1650,
                                vp_790 = vp_790,
                                vp_380 = vp_380,
                                vp_125 = vp_125,
                                load = load)
