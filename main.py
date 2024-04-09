# main.py
from modules.utils import prompt_for_search_parameters
from modules.selenium_utils import search_mops
from modules.data_fetcher import fetch_data_with_dynamic_payload
import time

def main():
    backoff_time = 1
    (
        tw_year,
        month,
        start_date,
        end_date,
        keyword1,
        keyword2,
        logic
    ) = prompt_for_search_parameters()
    additional_info = search_mops(
        tw_year, month, start_date, end_date, keyword1, keyword2, logic
    )
    print(len(additional_info))
    for onclick_js in additional_info:
        try:
            fetch_data_with_dynamic_payload(
                onclick_js, tw_year, month, start_date, end_date, keyword1, keyword2
            )
            backoff_time = max(
                1, backoff_time / 2
            )  # Reset or decrease the backoff time
        except IndexError:
            # If 'list index out of range' error occurs, simply pass and continue with the next item
            pass
        except Exception as e:
            # Handle other exceptions and retry with an increased backoff time
            print(f"Error: {e}. Retrying after {backoff_time} seconds.")
            time.sleep(backoff_time)
            backoff_time *= 2  # Exponentially increase the backoff time

if __name__ == "__main__":
    main()
