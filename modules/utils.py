# utils.py
import re
from modules.config import COLUMN_NAMES

def clean_text(text):
    text = re.sub(r"^\d+\.\s*", "", text)
    return text.replace("\r", "").replace("\n", "").replace("\xa0", " ").strip()

def generate_filename(tw_year, month, start_date, end_date, keyword1, keyword2=""):
    year_str = str(int(tw_year) + 1911)
    month_str = f"0{month}" if isinstance(month, int) and 1 <= int(month) <= 9 else (str(month) if 10 <= int(month) <= 12 else "ALL")
    start_date_str = str(start_date)
    end_date_str = str(end_date)
    keyword2_part = f"_{keyword2}" if keyword2 else ""
    return f"announce_d_{year_str}{month_str}_{start_date_str}_{end_date_str}_{keyword1}{keyword2_part}.csv"

def process_explanations(split_content, column_names=COLUMN_NAMES):
    explanations_dict = dict.fromkeys(column_names, None)
    for text in split_content:
        key, _, value = text.partition(":")
        cleaned_key = clean_text(key)
        cleaned_value = clean_text(value)
        if cleaned_key in column_names:
            explanations_dict[cleaned_key] = cleaned_value
    return [explanations_dict[key] for key in column_names]

def prompt_for_dates():
    while True:
        start_date = input("Enter the start date as an integer: ")
        end_date = input("Enter the end date as an integer: ")
        try:
            start_date, end_date = int(start_date), int(end_date)
            if start_date > end_date:
                print("Start date cannot be after end date. Please try again.")
            else:
                return start_date, end_date
        except ValueError:
            print("Both dates need to be integers. Please try again.")


def prompt_for_tw_year():
    while True:
        tw_year = input("Enter the Taiwan year (e.g., 110): ").strip()
        if tw_year:
            return tw_year
        print("The Taiwan year cannot be empty.")

def prompt_for_month():
    while True:
        month_input = input("Enter the month as an integer (1-12), or any other value to select every month: ").strip()
        if not month_input:
            print("The month cannot be empty.")
            continue
        try:
            month = int(month_input) if 1 <= int(month_input) <= 12 else 0
            return int(month)
        except ValueError:
            print("Invalid input for month. Please enter an integer between 1 and 12, or any other value to select every month.")

def prompt_for_keyword1():
    while True:
        keyword1 = input("Enter the first keyword: ").strip()
        if keyword1:
            return keyword1
        print("The first keyword cannot be empty.")

def prompt_for_keyword2():
    return input("Enter the second keyword (optional, press enter to skip): ").strip()

def prompt_for_search_parameters():
    tw_year = input("Enter the Taiwan year (e.g., 110): ")
    month = input("Enter the month as an integer (1-12), or any other value to select every month: ")
    start_date, end_date = prompt_for_dates()
    keyword1 = input("Enter the first keyword: ")
    keyword2 = input("Enter the second keyword (optional, press enter to skip): ")
    logic = input("Choose logical operation for keywords (1: AND, 2: OR, 3: NOT), press enter for default (AND): ")

    # Set default logic operation to AND (1) if invalid input is provided
    try:
        logic = int(logic)
        if logic not in [1, 2, 3]:
            raise ValueError
    except ValueError: 
        logic = 1  # Default to AND

    return tw_year, month, start_date, end_date, keyword1, keyword2, logic

