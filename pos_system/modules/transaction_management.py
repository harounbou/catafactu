# pos_system/modules/transaction_management.py
import pandas as pd
import json
from datetime import datetime
import streamlit as st
from .utils import read_csv, save_csv

TRANSACTIONS_FILE = "data/transactions.csv"
EXPENDITURES_FILE = "data/expenditures.csv"
STAFF_PAYMENTS_FILE = "data/staff_payments.csv"
TILL_FILE = "data/till.csv"

def record_transaction(client_info, items, payment_type, deposit_amount, total_amount, status="proforma"):
    df = read_csv(TRANSACTIONS_FILE)
    if df.empty:
        df = pd.DataFrame(columns=["transaction_id", "date", "client_id", "items", "total_amount", "status", "payment_type", "deposit_amount", "remaining_amount"])
    transaction_id = df["transaction_id"].max() + 1 if not df.empty else 1000
    remaining_amount = total_amount - deposit_amount if deposit_amount else 0
    new_transaction = {
        "transaction_id": transaction_id,
        "date": datetime.now().strftime("%d/%m/%Y"),
        "client_id": client_info["id_client"],
        "items": json.dumps(items),
        "total_amount": total_amount,
        "status": status,
        "payment_type": payment_type,
        "deposit_amount": deposit_amount or 0,
        "remaining_amount": remaining_amount
    }
    df = pd.concat([df, pd.DataFrame([new_transaction])], ignore_index=True)
    save_csv(df, TRANSACTIONS_FILE)
    update_till(deposit_amount or total_amount, "in", f"{status} Transaction {transaction_id}")
    return transaction_id

def record_expenditure(assistant_name, amount, description):
    df = read_csv(EXPENDITURES_FILE)
    if df.empty:
        df = pd.DataFrame(columns=["expenditure_id", "date", "assistant_name", "amount", "description"])
    expenditure_id = df["expenditure_id"].max() + 1 if not df.empty else 1
    new_expenditure = {
        "expenditure_id": expenditure_id,
        "date": datetime.now().strftime("%d/%m/%Y"),
        "assistant_name": assistant_name,
        "amount": amount,
        "description": description
    }
    df = pd.concat([df, pd.DataFrame([new_expenditure])], ignore_index=True)
    save_csv(df, EXPENDITURES_FILE)
    update_till(amount, "out", f"Expenditure {expenditure_id}")

def record_staff_payment(staff_name, amount):
    df = read_csv(STAFF_PAYMENTS_FILE)
    if df.empty:
        df = pd.DataFrame(columns=["payment_id", "date", "staff_name", "amount"])
    payment_id = df["payment_id"].max() + 1 if not df.empty else 1
    new_payment = {
        "payment_id": payment_id,
        "date": datetime.now().strftime("%d/%m/%Y"),
        "staff_name": staff_name,
        "amount": amount
    }
    df = pd.concat([df, pd.DataFrame([new_payment])], ignore_index=True)
    save_csv(df, STAFF_PAYMENTS_FILE)
    update_till(amount, "out", f"Staff Payment {payment_id}")

def update_till(amount, direction, description):
    df = read_csv(TILL_FILE)
    if df.empty:
        df = pd.DataFrame(columns=["date", "amount", "direction", "description", "balance"])
        balance = 0
    else:
        balance = df["balance"].iloc[-1]
    new_balance = balance + amount if direction == "in" else balance - amount
    new_entry = {
        "date": datetime.now().strftime("%d/%m/%Y"),
        "amount": amount,
        "direction": direction,
        "description": description,
        "balance": new_balance
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    save_csv(df, TILL_FILE)
    return new_balance

def get_till_balance():
    df = read_csv(TILL_FILE)
    return df["balance"].iloc[-1] if not df.empty else 0