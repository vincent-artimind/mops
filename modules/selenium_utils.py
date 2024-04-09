# selenium_utils.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def search_mops(tw_year, month, start_date, end_date, keyword1, keyword2=None, logic = 1):
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
    try:
        month_int = int(month)  # Attempt to convert month to an integer
        if 1 <= month_int <= 12:
            # Valid month number; select corresponding option (accounting for "All Months" option if present)
            month_option_xpath = f'//*[@id="search"]/table/tbody/tr[4]/td[2]/select/option[{month_int + 1}]'
        else:
            # Month number out of range; default to "All Months"
            month_option_xpath = '//*[@id="search"]/table/tbody/tr[4]/td[2]/select/option[1]'
    except ValueError:
        # Month input was not a number; default to "All Months"
        month_option_xpath = '//*[@id="search"]/table/tbody/tr[4]/td[2]/select/option[1]'

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

    # Assuming logic value is returned from prompt_for_search_parameters
    if int(logic) == 1:
        logic_option_xpath = '//*[@id="search"]/table/tbody/tr[3]/td/select/option[1]'  # AND
    elif int(logic) == 2:
        logic_option_xpath = '//*[@id="search"]/table/tbody/tr[3]/td/select/option[2]'  # OR
    else:
        logic_option_xpath = '//*[@id="search"]/table/tbody/tr[3]/td/select/option[3]'  # NOT

    wait.until(
            EC.element_to_be_clickable((By.XPATH, logic_option_xpath))
        ).click()

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
        # Keywords that indicate a post is not domestic
        exclude_keywords = ["Vietnam", "香港", "大陸", "India", "上海", "江蘇", "馬來西亞", "越南", "昆山", "蘇州", "深圳", "東莞", "萊州", "杭州", "南京", "泰國", "威海", "USA", "重慶", "惠州", "美國", "浙江", "北京", "寧波", "嘉興", "Mexico"]

        for row in rows:
            try:
                # Check the title in the fifth column
                title = row.find_element(By.XPATH, ".//td[5]").text
                # Skip rows where the title contains any of the exclude keywords
                if any(keyword in title for keyword in exclude_keywords):
                    continue  # Skip this iteration and don't collect onclick_attribute

                # If the row passed the check, find the button and collect its onclick attribute
                button = row.find_element(By.XPATH, ".//td[6]/input")
                onclick_attribute = button.get_attribute("onclick")
                collected_info.append(onclick_attribute)
            except Exception as e:
                print(f"Error collecting info: {e}")
        return collected_info

    def navigate_and_collect():
        additional_info = []
        initial_collected = collect_additional_info()
        additional_info.extend(initial_collected)
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
            additional_info.extend(collect_additional_info())
            for _ in range(2, total_pages + 1):
                try:
                    # Wait for any potential overlay to disappear before clicking the next page button
                    WebDriverWait(driver, 10).until(
                    EC.invisibility_of_element_located((By.ID, "dialog-mask")))
                    next_page_button_xpath = "/html/body/center/table/tbody/tr/td/div[4]/table/tbody/tr/td/div/table/tbody/tr/td[3]/div/div[5]/div/center/form/span/button[9]"
                    next_page_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, next_page_button_xpath))
                    )
                    next_page_button.click()
                    # Ensure the page has loaded new content. You might add a more specific condition here.
                    time.sleep(5) 
                    additional_info.extend(collect_additional_info())
                except (TimeoutException, StaleElementReferenceException) as e:
                    print(f"Error navigating to next page: {e}")
                    break
        else:            
            # Attempt navigation for 2 to 5 pages
            for page_num in range(
                2, 6
            ):  # Adjust the range to start from 3 to 6, corresponding to buttons for pages 2 to 5
                try:
                    page_button_xpath = f"/html/body/center/table/tbody/tr/td/div[4]/table/tbody/tr/td/div/table/tbody/tr/td[3]/div/div[5]/div/center/form/span/button[{page_num}]"
                    if wait.until(EC.element_to_be_clickable((By.XPATH, page_button_xpath))):
                        wait.until(EC.element_to_be_clickable((By.XPATH, page_button_xpath))).click()
                        time.sleep(5)
                        page_collected = collect_additional_info()
                        additional_info.extend(page_collected)
                except TimeoutException:
                    # If a specific page button is not found, it means we've navigated all available pages
                    break

        return additional_info

    # Collect 'additional_info' from all available pages
    additional_info = navigate_and_collect()
    print(len(additional_info))
    # Clean up
    driver.quit()

    return additional_info
