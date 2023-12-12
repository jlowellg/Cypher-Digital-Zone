CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    hash TEXT NOT NULL
);

CREATE TABLE stocks (
    stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    network TEXT NOT NULL,
    sim_name TEXT UNIQUE NOT NULL,
    sim_number TEXT UNIQUE NOT NULL,
    balance NUMERIC NOT NULL,
    date_added DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    load_amount NUMERIC NOT NULL,
    transaction_type TEXT NOT NULL,
    date DATETIME NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
);

CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    top_up_type TEXT NOT NULL,
    transaction_amount NUMERIC NOT NULL,
    transaction_load NUMERIC NOT NULL,
    discount NUMERIC NOT NULL,
    profit NUMERIC NOT NULL,
    transaction_date DATETIME NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stocks(stock_id)
);
