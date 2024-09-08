from datetime import datetime
from os import getenv
from pprint import pprint
from dotenv import load_dotenv
import gspread.spreadsheet
from requests import get
from throttlers import ynab_throttler
from throttlers.package_throttler import PackageThrottler
from throttlers.ynab_throttler import YNABThrottler
import json
import gspread
load_dotenv()


ynab_throttler = YNABThrottler(
    primary_api_key=getenv("YNAB_PAT"),
    backup_api_keys=[]
)

gspread_throttle = PackageThrottler(
    transient_exceptions=(gspread.exceptions.APIError),
    rate_limit_window=60,
    max_operations_in_window = 60
).execute_with_throttle

service_account = gspread_throttle(
    gspread,
    'service_account',
    'secret_personal-ynab_service_account.json'
)

spread = gspread_throttle(
    service_account,
    'open_by_key',
    '1Yn0uni4qacRCIrKlgEXzNVpL_VVF6Z895wynuIAR2LY'
)

sheet = gspread_throttle(
    spread,
    "get_worksheet_by_id",
    613545415
)

records = gspread_throttle(
    sheet,
    "get_all_records",
    head=2
)

pay_record = records[1]


pay_release = pay_record.get('Pay Release', '')  # 12/15/2024
pay_release_formatted = ''

if pay_release:
    date_obj = datetime.strptime(pay_release, '%m/%d/%Y')
    pay_release_formatted = date_obj.strftime('%Y-%m-%d')

amount = pay_record.get('Pay (PHP)', '') # 1000.00

transaction_data = {
    "transactions": []
}

# Define the date range
start_date = datetime(2024, 2, 1)
end_date = datetime.now()

for pay_record in records:
    pay_release = pay_record.get('Pay Release', '')  # 12/15/2024
    pay_release_formatted = ''

    if pay_release:
        try:
            date_obj = datetime.strptime(pay_release, '%m/%d/%Y')
            if start_date <= date_obj <= end_date:
                pay_release_formatted = date_obj.strftime('%Y-%m-%d')
            else:
                continue  # Skip this record if the date is out of range
        except ValueError:
            continue  # Skip this record if the date format is invalid

    amount = pay_record.get('Pay (PHP)', '')  # 1000.00

    if not amount:
        continue  # Skip this record if the amount is empty

    try:
        amount_value = float(amount)
    except ValueError:
        continue  # Skip this record if the amount is not a valid float

    pprint(pay_release_formatted)

    transaction_data['transactions'].append({
        "account_id": getenv("YNAB_ACCOUNT_BPI_ID"),
        "date": pay_release_formatted,
        "amount": int(amount_value * 1000),
        "payee_id": getenv("YNAB_PAYEE_MYAMAZONGUY_ID"),
        "category_id": getenv("YNAB_CATEGORY_ASSIGN_ID"),
        "cleared": "cleared",
        "flag_color": "green"
    })

pprint(transaction_data)


try:
    response = ynab_throttler.throttled_post(f'https://api.ynab.com/v1/budgets/{getenv("YNAB_BUDGET_ID")}/transactions', json=transaction_data)
    pprint(response.json())
except Exception as e:
    pprint(e)
