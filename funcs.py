from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp

from helpers import *


def get_user_stocks():
    stocks = db.execute("SELECT * FROM portfolio WHERE owner = :id", id=session['user_id'])
    return stocks
    

def remove_empty_stocks():
    db.execute("DELETE FROM portfolio WHERE amount<=0")
    
def get_cash_balance():
    return db.execute("SELECT cash FROM users WHERE id=:id", id=session['user_id'])

    
    
def amount_shares(symbol):
    return db.execute("SELECT amount from portfolio WHERE owner = :id AND symbol = :symbol", id=session["user_id"], symbol=symbol)

def cash_minus_value(total):
    db.execute("UPDATE users SET cash = cash - :total WHERE id = :id", total=total, id=session["user_id"])


def insert_history(a,b,c,d):
    db.execute("INSERT INTO history(buyorsell, symbol, price, owner, shares) VALUES (:buyorsell, :symbol, :price, :owner, :shares)", buyorsell=a, symbol=b, price=c, owner=session['user_id'], shares=d)
    
def get_history():
    return db.execute("SELECT * FROM history WHERE owner=:id", id=session['user_id'])