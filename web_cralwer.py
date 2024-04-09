import os
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (StaleElementReferenceException,
                                        TimeoutException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

global_aggregated_df = pd.DataFrame()
backoff_time = 1
execution_count = 0
column_names = [
    "標的物之名稱及性質（如坐落台中市北區ＸＸ段ＸＸ小段土地）",
    "事實發生日",
    "交易單位數量（如ＸＸ平方公尺，折合ＸＸ坪）、每單位價格及交易總金額",
    "交易相對人及其與公司之關係（交易相對人如屬自然人，且非公司之關係人者，得免揭露其姓名）",
    "交易相對人為關係人者，並應公告選定關係人為交易對象之原因及前次移轉之所有人、前次移轉之所有人與公司及交易相對人間相互之關係、前次移轉日期及移轉金額",
    "交易標的最近五年內所有權人曾為公司之關係人者，尚應公告關係人之取得及處分日期、價格及交易當時與公司之關係",
    "預計處分利益（或損失）（取得資產者不適用）（遞延者應列表說明認列情形）",
    "交付或付款條件（含付款期間及金額）、契約限制條款及其他重要約定事項",
    "本次交易之決定方式（如招標、比價或議價）、價格決定之參考依據及決策單位",
    "專業估價者事務所或公司名稱及其估價金額",
    "專業估價師姓名",
    "專業估價師開業證書字號",
    "估價報告是否為限定價格、特定價格或特殊價格",
    "是否尚未取得估價報告",
    "尚未取得估價報告之原因",
    "估價結果有重大差異時，其差異原因及會計師意見",
    "會計師事務所名稱",
    "會計師姓名",
    "會計師開業證書字號",
    "經紀人及經紀費用",
    "取得或處分之具體目的或用途",
    "本次交易表示異議之董事之意見",
    "本次交易為關係人交易",
    "董事會通過日期",
    "監察人承認或審計委員會同意日期",
    "本次交易係向關係人取得不動產或其使用權資產",
    "依「公開發行公司取得或處分資產處理準則」第十六條規定評估之價格",
    "依前項評估之價格較交易價格為低者，依同準則第十七條規定評估之價格",
    "其他敘明事項",
]


def clean_text(text):
    text = re.sub(r"^\d+\.\s*", "", text)
    return text.replace("\r", "").replace("\n", "").replace("\xa0", " ").strip()


def process_explanations(split_content, column_names):
    explanations_dict = dict.fromkeys(column_names, None)
    for text in split_content:
        key, _, value = text.partition(":")
        cleaned_key = clean_text(key)
        cleaned_value = clean_text(value)
        if cleaned_key in column_names:
            explanations_dict[cleaned_key] = cleaned_value
    return [explanations_dict[key] for key in column_names]


def generate_filename(tw_year, month, start_date, end_date, keyword1, keyword2=""):
    year_str = str(int(tw_year) + 1911)
    month_str = f"0{month}" if isinstance(month, int) and month < 10 else str(month)
    start_date_str = str(start_date)
    end_date_str = str(end_date)
    keyword2_part = f"_{keyword2}" if keyword2 else ""
    return f"announce_d_{year_str}{month_str}_{start_date_str}_{end_date_str}_{keyword1}{keyword2_part}.csv"


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


def prompt_for_search_parameters():
    tw_year = input("Enter the Taiwan year (e.g., 110): ")
    month = input(
        "Enter the month as an integer (1-12), or any other value to select every month: "
    )
    keyword1 = input("Enter the first keyword: ")
    keyword2 = input("Enter the second keyword (optional, press enter to skip): ")
    try:
        month = int(month) if month.isdigit() and 1 <= int(month) <= 12 else "0"
    except ValueError:
        month = "all"
    start_date, end_date = prompt_for_dates()
    return tw_year, month, start_date, end_date, keyword1, keyword2 or ""


def search_mops(tw_year, month, start_date, end_date, keyword1, keyword2=None):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Uncomment if you don't want to see the browser window

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    url = "https://mops.twse.com.tw/mops/web/t51sb10_q1"
    driver.get(url)
    time.sleep(5)
    wait = WebDriverWait(driver, 10)

    # First, click the specified input field
    initial_click_xpath = '//*[@id="search"]/table/tbody/tr[2]/td[1]/input'
    driver.find_element(By.XPATH, initial_click_xpath).click()

    time.sleep(5)

    # Year input (Taiwan year)
    year_input_xpath = '//*[@id="search"]/table/tbody/tr[4]/td[1]/input'
    year_input_field = driver.find_element(By.XPATH, year_input_xpath)
    year_input_field.clear()  # Clear any pre-filled text in the input field
    year_input_field.send_keys(
        str(tw_year)
    )  # Convert the Taiwanese year to a string and enter it

    # Month selection
    if isinstance(month, int) and 1 <= month <= 12:
        month_option_xpath = (
            f'//*[@id="search"]/table/tbody/tr[4]/td[2]/select/option[{month + 1}]'
        )
    else:
        month_option_xpath = (
            '//*[@id="search"]/table/tbody/tr[4]/td[2]/select/option[1]'
        )
    wait.until(EC.element_to_be_clickable((By.XPATH, month_option_xpath))).click()

    # Start date selection
    if (
        isinstance(start_date, int)
        and isinstance(end_date, int)
        and start_date <= end_date
    ):
        start_date_option_xpath = (
            f'//*[@id="search"]/table/tbody/tr[4]/td[3]/select/option[{start_date}]'
        )
        wait.until(
            EC.element_to_be_clickable((By.XPATH, start_date_option_xpath))
        ).click()

        end_date_option_xpath = (
            f'//*[@id="search"]/table/tbody/tr[4]/td[4]/select/option[{end_date}]'
        )
        wait.until(
            EC.element_to_be_clickable((By.XPATH, end_date_option_xpath))
        ).click()
    else:
        print("Invalid date range provided.")

    # Keyword 1 input
    keyword1_input = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, '//*[@id="search"]/table/tbody/tr[3]/td/input[1]')
        )
    )
    keyword1_input.send_keys(keyword1)

    option_xpath_for_and = '//*[@id="search"]/table/tbody/tr[3]/td/select/option[1]'
    driver.find_element(By.XPATH, option_xpath_for_and).click()

    # Keyword 2 input (optional)
    if keyword2:
        keyword2_input = driver.find_element(
            By.XPATH, '//*[@id="search"]/table/tbody/tr[3]/td/input[2]'
        )
        keyword2_input.send_keys(keyword2)

    # Search action
    search_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="search_bar1"]/div/input'))
    )
    search_button.click()

    # Wait for the page to load results
    wait = WebDriverWait(driver, 10)

    def collect_additional_info():
        collected_info = []
        rows = driver.find_elements(By.XPATH, '//*[@id="myTable"]/tbody/tr')
        for row in rows:
            try:
                button = row.find_element(By.XPATH, ".//td[6]/input")
                onclick_attribute = button.get_attribute("onclick")
                collected_info.append(onclick_attribute)
            except Exception as e:
                print(f"Error collecting info: {e}")
        return collected_info

    def navigate_and_collect():
        additional_info = []
        # Check for total pages indicator for more than five pages
        try:
            total_pages_indicator = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/center/table/tbody/tr/td/div[4]/table/tbody/tr/td/div/table/tbody/tr/td[3]/div/div[5]/div/center/form/span/button[11]",
                    )
                )
            ).text
            total_pages = int(total_pages_indicator)
            multiple_pages = True
        except (TimeoutException, ValueError):
            multiple_pages = False

        if multiple_pages and total_pages > 1:
            for _ in range(total_pages - 1):
                additional_info.extend(collect_additional_info())
                try:
                    next_page_button_xpath = "/html/body/center/table/tbody/tr/td/div[4]/table/tbody/tr/td/div/table/tbody/tr/td[3]/div/div[5]/div/center/form/span/button[9]"
                    next_page_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, next_page_button_xpath))
                    )
                    next_page_button.click()
                    # Ensure the page has loaded new content. You might add a more specific condition here.
                    wait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, '//*[contains(@class, "new-content-indicator")]')
                        )
                    )
                    additional_info.extend(collect_additional_info())
                except (TimeoutException, StaleElementReferenceException):
                    print("Error navigating to next page.")
                    break
        else:
            # Handle first page separately
            additional_info.extend(collect_additional_info())
            # Attempt navigation for 2 to 5 pages
            for page_num in range(
                3, 7
            ):  # Adjust the range to start from 3 to 6, corresponding to buttons for pages 2 to 5
                try:
                    page_button_xpath = f"/html/body/center/table/tbody/tr/td/div[4]/table/tbody/tr/td/div/table/tbody/tr/td[3]/div/div[5]/div/center/form/span/button[{page_num}]"
                    page_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, page_button_xpath))
                    )

                    # Check if the text of the button is an integer before clicking
                    if page_button.text.isdigit():
                        page_button.click()
                        time.sleep(5)  # Wait for the page to load
                        additional_info.extend(collect_additional_info())
                    else:
                        break  # If the text is not an integer, exit the loop
                except TimeoutException:
                    break  # If the button is not clickable or does not exist, exit the loop

        return additional_info

    # Collect 'additional_info' from all available pages
    additional_info = navigate_and_collect()

    # Clean up
    driver.quit()

    return additional_info


def fetch_data_with_dynamic_payload(
    onclick_js, tw_year, month, start_date, end_date, keyword1, keyword2=""
):
    global backoff_time
    global global_aggregated_df
    global execution_count  # Indicate that we're using the global variable
    execution_count += 1  # Increment the counter each time the function is called

    # Calculate the page number based on the execution count
    # Assuming the first page starts at 1 and increments every 15 executions
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
    split_content = re.split(r"\n(?=\d+\.)", content)
    explanations_list = [clean_text(part) for part in split_content if part.strip()]
    explanations = process_explanations(explanations_list, column_names)

    # Extracting co_id and name
    comp_element = soup.find(class_="compName")
    pattern = re.compile(r"\(\上市公司\)\s*(\d+)\s+(\w+)")
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
        + column_names
    )
    df = pd.DataFrame([all_data], columns=columns)

    global_aggregated_df = pd.concat([global_aggregated_df, df], ignore_index=True)

    file_path = os.path.join(
        "/Users/yuchengweng/ArtiMind",
        generate_filename(tw_year, month, start_date, end_date, keyword1, keyword2),
    )

    global_aggregated_df.to_csv(file_path, index=True)


def main():
    global backoff_time
    (
        tw_year,
        month,
        start_date,
        end_date,
        keyword1,
        keyword2,
    ) = prompt_for_search_parameters()
    additional_info = search_mops(
        tw_year, month, start_date, end_date, keyword1, keyword2
    )

    for onclick_js in additional_info:
        try:
            fetch_data_with_dynamic_payload(
                onclick_js, tw_year, month, start_date, end_date, keyword1, keyword2
            )
            backoff_time = max(
                1, backoff_time / 2
            )  # Reset or decrease the backoff time
        except Exception as e:
            print(f"Error: {e}. Retrying after {backoff_time} seconds.")
            time.sleep(backoff_time)
            backoff_time *= 2  # Exponentially increase the backoff time


if __name__ == "__main__":
    main()
