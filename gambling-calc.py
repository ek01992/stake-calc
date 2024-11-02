#!/usr/bin/env python3

import csv
import sys
import requests
import os
import argparse
import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
from babel.numbers import format_currency
from babel.dates import format_datetime
import time

def get_historical_exchange_rates(currencies, date_ranges):
    # Map currency symbols to CoinGecko IDs
    currency_map = {
        'btc': 'bitcoin',
        'eth': 'ethereum',
        'usdt': 'tether',
        'usdc': 'usd-coin',
        'bnb': 'binancecoin',
        'xrp': 'ripple',
        'ada': 'cardano',
        'sol': 'solana',
        'doge': 'dogecoin',
        'dot': 'polkadot',
        'matic': 'polygon',
        'shib': 'shiba-inu',
        'ltc': 'litecoin',
        'trx': 'tron',
        'avax': 'avalanche-2',
        'uni': 'uniswap',
        'wbtc': 'wrapped-bitcoin',
        'link': 'chainlink',
        'atom': 'cosmos',
        'etc': 'ethereum-classic',
        'xmr': 'monero',
        'bch': 'bitcoin-cash',
        'algo': 'algorand',
        'fil': 'filecoin',
        'apt': 'aptos',
        'qnt': 'quant-network',
        'vet': 'vechain',
        'icp': 'internet-computer',
        'near': 'near',
        'egld': 'elrond-erd-2',
        # Add more currencies as needed
    }

    exchange_rates = {}
    for currency in currencies:
        currency_id = currency_map.get(currency.lower())
        if not currency_id:
            print(f"Currency {currency} is not supported.")
            sys.exit(1)

        start_date = date_ranges[currency]['start_date']
        end_date = date_ranges[currency]['end_date']

        # Convert dates to UNIX timestamps
        from_timestamp = int(datetime.datetime.combine(start_date, datetime.time.min).timestamp())
        to_timestamp = int(datetime.datetime.combine(end_date + datetime.timedelta(days=1), datetime.time.min).timestamp())

        # Prepare API URL
        url = f'https://api.coingecko.com/api/v3/coins/{currency_id}/market_chart/range?vs_currency=usd&from={from_timestamp}&to={to_timestamp}'

        # Fetch data with retry mechanism
        success = False
        retries = 0
        max_retries = 5
        while not success and retries < max_retries:
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                success = True
            except requests.RequestException as e:
                retries += 1
                wait_time = retries * 2  # Exponential backoff
                print(f"Error fetching data: {e}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

        if not success:
            print(f"Failed to fetch data for {currency} after {max_retries} retries.")
            sys.exit(1)

        # Process the data to extract daily prices
        prices = data.get('prices', [])
        daily_rates = {}
        for price in prices:
            timestamp = price[0] / 1000  # Convert milliseconds to seconds
            date = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc).date()
            rate = price[1]
            daily_rates[date] = rate

        # Fill missing dates
        all_dates = [start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days + 1)]
        last_known_rate = None
        for date in all_dates:
            if date in daily_rates:
                last_known_rate = daily_rates[date]
            else:
                if last_known_rate is not None:
                    daily_rates[date] = last_known_rate
                else:
                    # If no rate is known yet, find the next available rate
                    future_dates = [d for d in daily_rates.keys() if d > date]
                    if future_dates:
                        next_date = min(future_dates)
                        daily_rates[date] = daily_rates[next_date]
                    else:
                        print(f"No exchange rate data available for {currency} on {date}")
                        sys.exit(1)

        exchange_rates[currency.lower()] = daily_rates

        # Respect rate limits
        time.sleep(1)  # Wait 1 second between API calls

    return exchange_rates

def parse_date(date_str):
    # Remove the timezone in parentheses
    if '(' in date_str:
        date_str = date_str[:date_str.find('(')].strip()
    # Replace 'GMT' with '' to isolate the UTC offset
    date_str = date_str.replace('GMT', '').strip()
    # Now the date string is like 'Fri Oct 04 2024 13:39:39 +0000'
    try:
        return datetime.datetime.strptime(date_str, '%a %b %d %Y %H:%M:%S %z')
    except ValueError:
        print(f"Error parsing date: {date_str}")
        sys.exit(1)

def read_transactions(filename):
    transactions = []
    currencies = set()
    dates = defaultdict(set)
    try:
        # Use absolute path
        filename = os.path.abspath(filename)
        with open(filename, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                amount = float(row['amount'])
                currency = row['currency'].lower()
                date = parse_date(row['date'])
                currencies.add(currency)
                transactions.append({'amount': amount, 'currency': currency, 'date': date})
                dates[currency].add(date.date())
        return transactions, currencies, dates
    except FileNotFoundError:
        print(f"File not found: {filename}")
        sys.exit(1)
    except KeyError as e:
        print(f"Missing expected column {e} in {filename}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        sys.exit(1)

def get_closest_rate(rates_dict, target_date):
    if target_date in rates_dict:
        return rates_dict[target_date]
    else:
        # Find the closest date
        available_dates = sorted(rates_dict.keys())
        before_dates = [d for d in available_dates if d < target_date]
        after_dates = [d for d in available_dates if d > target_date]
        if before_dates and after_dates:
            prev_date = before_dates[-1]
            next_date = after_dates[0]
            # Choose the closest date
            if (target_date - prev_date) <= (next_date - target_date):
                return rates_dict[prev_date]
            else:
                return rates_dict[next_date]
        elif before_dates:
            return rates_dict[before_dates[-1]]
        elif after_dates:
            return rates_dict[after_dates[0]]
        else:
            return None

def calculate_statistics(transactions, exchange_rates, locale):
    total_usd = 0.0
    amounts_usd = []
    dates = []
    daily_totals = defaultdict(float)
    updated_transactions = []
    for tx in transactions:
        date = tx['date'].date()
        rate = get_closest_rate(exchange_rates[tx['currency']], date)
        if rate is None:
            print(f"No exchange rate available for {tx['currency']} near {date}")
            sys.exit(1)
        usd_amount = tx['amount'] * rate
        total_usd += usd_amount
        amounts_usd.append(usd_amount)
        dates.append(tx['date'])
        daily_totals[date] += usd_amount
        tx['usd_amount'] = usd_amount  # Add usd_amount to transaction
        updated_transactions.append(tx)
    # Sort transactions by date
    updated_transactions.sort(key=lambda x: x['date'])
    return total_usd, amounts_usd, dates, daily_totals, updated_transactions

def format_currency_local(value, locale):
    return format_currency(value, 'USD', locale=locale)

def compute_averages(amounts, dates):
    if not dates:
        return {}
    dates.sort()
    first_date = dates[0].date()
    last_date = dates[-1].date()
    total_days = (last_date - first_date).days + 1  # Include both first and last day

    if total_days >= 7:
        total_weeks = total_days / 7
    else:
        total_weeks = 1

    if total_days >= 30:
        total_months = total_days / 30.44  # Average days in a month
    else:
        total_months = 1

    if total_days >= 365:
        total_years = total_days / 365.25  # Accounting for leap years
    else:
        total_years = 1

    avg_per_week = sum(amounts) / total_weeks
    avg_per_month = sum(amounts) / total_months
    avg_per_year = sum(amounts) / total_years

    return {
        'avg_per_week': avg_per_week,
        'avg_per_month': avg_per_month,
        'avg_per_year': avg_per_year
    }

def output_results(purchases, redemptions, exchange_rates, locale, output_file=None):
    # Calculate statistics for purchases and redemptions
    total_deposits_usd, deposit_amounts_usd, deposit_dates, deposit_daily_totals, updated_purchases = calculate_statistics(purchases, exchange_rates, locale)
    total_withdrawals_usd, withdrawal_amounts_usd, withdrawal_dates, withdrawal_daily_totals, updated_redemptions = calculate_statistics(redemptions, exchange_rates, locale)

    net_result = total_withdrawals_usd - total_deposits_usd

    # Prepare output data
    output_lines = []

    # Filter out zero-amount transactions
    non_zero_deposits = [tx for tx in updated_purchases if tx['usd_amount'] > 0]
    non_zero_withdrawals = [tx for tx in updated_redemptions if tx['usd_amount'] > 0]

    # Deposit statistics
    if deposit_dates and non_zero_deposits:
        first_deposit = updated_purchases[0]
        last_deposit = updated_purchases[-1]
        min_deposit = min(non_zero_deposits, key=lambda x: x['usd_amount'])
        max_deposit = max(non_zero_deposits, key=lambda x: x['usd_amount'])
        deposit_averages = compute_averages(deposit_amounts_usd, deposit_dates)

        output_lines.append(f"First Deposit: {format_datetime(first_deposit['date'], locale=locale)} - {format_currency_local(first_deposit['usd_amount'], locale)}")
        output_lines.append(f"Most Recent Deposit: {format_datetime(last_deposit['date'], locale=locale)} - {format_currency_local(last_deposit['usd_amount'], locale)}")
        output_lines.append(f"Smallest Deposit: {format_currency_local(min_deposit['usd_amount'], locale)}")
        output_lines.append(f"Largest Deposit: {format_currency_local(max_deposit['usd_amount'], locale)}")
        output_lines.append(f"Average Deposit per Week: {format_currency_local(deposit_averages['avg_per_week'], locale)}")
        output_lines.append(f"Average Deposit per Month: {format_currency_local(deposit_averages['avg_per_month'], locale)}")
        if len(deposit_dates) > 365:
            output_lines.append(f"Average Deposit per Year: {format_currency_local(deposit_averages['avg_per_year'], locale)}")
        output_lines.append("")
    else:
        output_lines.append("No deposit transactions found.")
        output_lines.append("")

    # Withdrawal statistics
    if withdrawal_dates and non_zero_withdrawals:
        first_withdrawal = updated_redemptions[0]
        last_withdrawal = updated_redemptions[-1]
        min_withdrawal = min(non_zero_withdrawals, key=lambda x: x['usd_amount'])
        max_withdrawal = max(non_zero_withdrawals, key=lambda x: x['usd_amount'])
        withdrawal_averages = compute_averages(withdrawal_amounts_usd, withdrawal_dates)

        output_lines.append(f"First Withdrawal: {format_datetime(first_withdrawal['date'], locale=locale)} - {format_currency_local(first_withdrawal['usd_amount'], locale)}")
        output_lines.append(f"Most Recent Withdrawal: {format_datetime(last_withdrawal['date'], locale=locale)} - {format_currency_local(last_withdrawal['usd_amount'], locale)}")
        output_lines.append(f"Smallest Withdrawal: {format_currency_local(min_withdrawal['usd_amount'], locale)}")
        output_lines.append(f"Largest Withdrawal: {format_currency_local(max_withdrawal['usd_amount'], locale)}")
        output_lines.append(f"Average Withdrawal per Week: {format_currency_local(withdrawal_averages['avg_per_week'], locale)}")
        output_lines.append(f"Average Withdrawal per Month: {format_currency_local(withdrawal_averages['avg_per_month'], locale)}")
        if len(withdrawal_dates) > 365:
            output_lines.append(f"Average Withdrawal per Year: {format_currency_local(withdrawal_averages['avg_per_year'], locale)}")
        output_lines.append("")
    else:
        output_lines.append("No withdrawal transactions found.")
        output_lines.append("")

    # Total amounts
    output_lines.append(f"Total Deposits (USD): {format_currency_local(total_deposits_usd, locale)}")
    output_lines.append(f"Total Withdrawals (USD): {format_currency_local(total_withdrawals_usd, locale)}")
    if net_result > 0:
        output_lines.append(f"Total Winnings (USD): {format_currency_local(net_result, locale)}")
    else:
        output_lines.append(f"Total Losses (USD): {format_currency_local(-net_result, locale)}")

    # Output to console or file
    output_text = '\n'.join(output_lines)
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
            print(f"Results have been written to {output_file}")
        except Exception as e:
            print(f"Error writing to file {output_file}: {e}")
            sys.exit(1)
    else:
        print(output_text)

    # Generate graphs
    generate_graphs(deposit_daily_totals, withdrawal_daily_totals, net_result, locale)

def generate_graphs(deposit_daily_totals, withdrawal_daily_totals, net_result, locale):
    dates = sorted(set(deposit_daily_totals.keys()).union(withdrawal_daily_totals.keys()))
    net_balances = []
    cumulative_balance = 0.0
    deposits = []
    withdrawals = []
    for date in dates:
        deposit = deposit_daily_totals.get(date, 0.0)
        withdrawal = withdrawal_daily_totals.get(date, 0.0)
        cumulative_balance += (withdrawal - deposit)
        net_balances.append(cumulative_balance)
        deposits.append(deposit)
        withdrawals.append(withdrawal)

    # Convert dates to matplotlib date format
    dates_datetime = [datetime.datetime.combine(date, datetime.time.min) for date in dates]

    plt.figure(figsize=(12, 6))

    plt.plot(dates_datetime, net_balances, label='Net Balance', marker='o')
    plt.bar(dates_datetime, deposits, width=1.0, label='Deposits', alpha=0.5)
    plt.bar(dates_datetime, [-w for w in withdrawals], width=1.0, label='Withdrawals', alpha=0.5)

    plt.xlabel('Date')
    plt.ylabel('Amount (USD)')
    plt.title('Gambling Activity Over Time')
    plt.legend()
    plt.tight_layout()
    plt.show()

def find_csv_files():
    files = os.listdir('.')
    purchases_file = None
    redemptions_file = None
    for file in files:
        if file.endswith('-crypto-purchases.csv'):
            purchases_file = file
        elif file.endswith('-crypto-redemptions.csv'):
            redemptions_file = file
    return purchases_file, redemptions_file

def main():
    parser = argparse.ArgumentParser(description='Calculate total gambling wins/losses from Stake.us transactions.')
    parser.add_argument('-p', '--purchases', help='Purchases CSV file')
    parser.add_argument('-r', '--redemptions', help='Redemptions CSV file')
    parser.add_argument('-o', '--output', help='Output file for results')
    parser.add_argument('-l', '--locale', default='en_US', help='Locale for date and currency formatting (e.g., en_US, fr_FR)')

    args = parser.parse_args()

    locale = args.locale

    if args.purchases and args.redemptions:
        purchases_file = args.purchases
        redemptions_file = args.redemptions
    else:
        purchases_file, redemptions_file = find_csv_files()
        if not purchases_file or not redemptions_file:
            print("Error: Could not find purchases and redemptions CSV files in the current directory.")
            print("Please specify the files using -p and -r options.")
            sys.exit(1)

    # Read purchases and redemptions
    purchases, purchase_currencies, purchase_dates = read_transactions(purchases_file)
    redemptions, redemption_currencies, redemption_dates = read_transactions(redemptions_file)

    # Get all unique currencies and their date ranges
    all_currencies = purchase_currencies.union(redemption_currencies)
    date_ranges = {}
    for currency in all_currencies:
        dates = purchase_dates.get(currency, set()).union(redemption_dates.get(currency, set()))
        if dates:
            date_ranges[currency] = {
                'start_date': min(dates),
                'end_date': max(dates)
            }
        else:
            print(f"No dates found for currency: {currency}")
            sys.exit(1)

    # Get exchange rates
    exchange_rates = get_historical_exchange_rates(all_currencies, date_ranges)

    # Output results
    output_results(purchases, redemptions, exchange_rates, locale, output_file=args.output)

if __name__ == "__main__":
    main()
