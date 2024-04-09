# data_fetcher.py
import pandas as pd
import requests
import re
import os
from bs4 import BeautifulSoup
from modules.utils import clean_text, process_explanations, generate_filename
from modules.config import MOPS_URL, USER_AGENT, COLUMN_NAMES

execution_count = 0 
global_aggregated_df = pd.DataFrame()

def fetch_data_with_dynamic_payload(onclick_js, tw_year, month, start_date, end_date, keyword1, keyword2=""):
    global backoff_time
    global global_aggregated_df
    global execution_count  # Indicate that we're using the global variable
    execution_count += 1  # Increment the counter each time the function is called

    # Calculate the page number based on the execution count
    # Assuming the first page starts at 1 and inc
    # ments every 15 executions
    pagenum = (execution_count - 1) // 15 + 1

    # Parse the onclick JavaScript to extract dynamic values
    extracted_values = {}
    patterns = {
        "seq_no": r"seq_no.value=\"(\d+)\";",
        "spoke_time": r"spoke_time.value=\"(\d+)\";",
        "spoke_date": r"spoke_date.value=\"(\d+)\";",
        "i": r"i.value=\"(\d+)\";",
        "co_id": r"co_id.value=\"(\d+)\";",
        "TYPEK": r"TYPEK.value=\"(sii)\";",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, onclick_js)
        if match:
            extracted_values[key] = match.group(1)

    # Define the URL
    url = "https://mops.twse.com.tw/mops/web/ajax_t05st01"

    # Update payload with dynamically extracted values and the dynamically determined page number
    payload = {
        "pagenum": str(pagenum),  # Update this dynamically
        "Stp": "4",
        "r1": "1",
        "KIND": "L",
        "CODE": "",
        "month1": str(month) if 1 <= int(month) <= 12 else "0",
        "begin_day": str(start_date),
        "end_day": str(end_date),
        "keyWord": keyword1,
        "Condition2": "1",
        "keyWord2": keyword2,
        "Orderby": "1",
        "step": "2",
        "colorchg": "1",
        **extracted_values,  # Unpack the dynamically extracted values here
        "off": "1",
        "firstin": "1",
        "year": str(int(tw_year) + 1911),
        "month": str(month) if 1 <= int(month) <= 12 else "0",
        "b_date": str(start_date),
        "e_date": str(end_date),
    }

    # Headers to simulate the browser request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    response = requests.post(url, data=payload, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    # Extract basic data elements
    odd_elements = soup.find_all(class_="odd")
    basic_data = [clean_text(elem.text) for elem in odd_elements[:9]]

    # Extract and handle explanations
    content = odd_elements[9].text.strip()
    currency_indicators = ["USD", "美金", "CNY", "RMB", "人民幣", "HKD", "MXN", "馬幣", "PHP", "泰銖", "歐元", "盧比", "越南盾"]
    if any(currency in content for currency in currency_indicators):
        return  # Skip further processing and saving of this post

    split_content = re.split(r"\n(?=\d+\.)", content)
    explanations_list = [clean_text(part) for part in split_content if part.strip()]
    explanations = process_explanations(explanations_list, COLUMN_NAMES)

    # Extracting co_id and name
    comp_element = soup.find(class_="compName")
    pattern = re.compile(r"\(\上市公司\)\s*(\d+)\s+([\w-]+)")
    co_id = None
    name = None
    if comp_element:
        comp_text = comp_element.text.strip()
        match = pattern.search(comp_text)
        if match:
            co_id = match.group(1)
            name = match.group(2)

    # Place co_id and name at the beginning of the data list
    all_data = [co_id, name] + basic_data + explanations

    # Adjust the columns list to include 'co_id' and 'name' at the beginning
    columns = (
        ["公司代號", "公司名稱"]
        + ["序號", "發言日期", "發言時間", "發言人", "發言人職稱", "發言人電話", "主旨", "符合條款", "事實發生日"]
        + COLUMN_NAMES
    )
    df = pd.DataFrame([all_data], columns=columns)

    global_aggregated_df = pd.concat([global_aggregated_df, df], ignore_index=True)

    file_path = os.path.join(
        "/Users/yuchengweng/ArtiMind",
        generate_filename(tw_year, month, start_date, end_date, keyword1, keyword2),
    )

    global_aggregated_df.to_csv(file_path, index=True)