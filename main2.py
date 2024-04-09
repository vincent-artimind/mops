from modules.selenium_utils import search_mops
from modules.data_fetcher import fetch_data_with_dynamic_payload
import time

def generate_search_parameters():
    search_params_list = []
    year_range = range(101, 114)  # From year 100 to 113
    criteria = [
        (13, 1, 31, '取得', '使用權', 1),
        # (13, 1, 31, '取得', '不動產', 1),
        # (13, 1, 31, '取得', '土地', 1),
        # (13, 1, 31, '承購', '', 1),
        # (13, 1, 31, '處分', '出售', 2),
    ]

    for year in year_range:
        for criterion in criteria:
            # Replace 'year' placeholder with actual year value in each criterion
            search_params = (year,) + criterion
            search_params_list.append(search_params)

    return search_params_list

def main():
    backoff_time = 1
    search_parameters = generate_search_parameters()

    for params in search_parameters:
        tw_year, month, start_date, end_date, keyword1, keyword2, logic = params
        try:
            additional_info = search_mops(tw_year, month, start_date, end_date, keyword1, keyword2, logic)
            for onclick_js in additional_info:
                try:
                    fetch_data_with_dynamic_payload(onclick_js, tw_year, month, start_date, end_date, keyword1, keyword2)
                    backoff_time = max(1, backoff_time / 2)  # Reset or decrease the backoff time
                except IndexError:
                    # If 'list index out of range' error occurs, simply pass and continue with the next item
                    pass
                except Exception as e:
                    # Handle other exceptions and retry with an increased backoff time
                    print(f"Error: {e}. Retrying after {backoff_time} seconds.")
                    time.sleep(backoff_time)
                    backoff_time *= 2  # Exponentially increase the backoff time
        except Exception as e:
            print(f"Error during search_mops: {e}")

if __name__ == "__main__":
    main()
