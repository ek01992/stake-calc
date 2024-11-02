# Stake Win/Loss Calculator

This script calculates total gambling wins/losses from Stake.us transactions, including historical exchange rates, and generates graphical output of your gambling activity over time.

## Features

- **Historical Exchange Rates**: Fetches historical exchange rates for cryptocurrencies from the CoinGecko API.
- **Multiple Currencies Support**: Supports transactions in multiple cryptocurrencies.
- **Graphical Output**: Generates graphs displaying net balance over time and daily deposits/withdrawals.
- **Localization**: Provides localized formatting for dates and currencies using the Babel library.
- **Detailed Statistics**: Outputs statistics including total deposits, withdrawals, winnings/losses, and averages per week/month/year.

## Requirements

- **Python**: Version 3.6 or higher.
- **Python Packages**:
  - `requests`
  - `matplotlib`
  - `babel`

## Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/ek01992/gambling-calc.git
   cd gambling-calc
   ```

2. **Install the Required Python Packages**:

   ```bash
   pip install -r requirements.txt
   ```

   If you prefer installing packages individually:

   ```bash
   pip install requests matplotlib babel
   ```

## Usage

1. **Prepare Your CSV Files**:

   - Place your `*-crypto-purchases.csv` and `*-crypto-redemptions.csv` files in the same directory as the script.

2. **Run the Script**:

   ```bash
   python gambling_calc.py
   ```

   - The script will automatically find the CSV files in the current directory.

3. **Specify CSV Files Explicitly**:

   If your CSV files have different names or are in different locations, specify them using command-line arguments:

   ```bash
   python gambling_calc.py -p path/to/purchases.csv -r path/to/redemptions.csv
   ```

4. **Specify Output File and Locale**:

   - To output results to a file:

     ```bash
     python gambling_calc.py -o results.txt
     ```

   - To specify a locale for date and currency formatting:

     ```bash
     python gambling_calc.py -l en_US
     ```

5. **Combining Options**:

   ```bash
   python gambling_calc.py -p purchases.csv -r redemptions.csv -o results.txt -l fr_FR
   ```

6. **Viewing Graphs**:

   - The script will display graphs of your gambling activity.
   - Close the graph window to allow the script to continue or terminate.

## Notes

- **API Rate Limits**:

  - The CoinGecko API has rate limits. The script includes a delay between API calls to respect these limits.
  - If you have many transactions over a wide date range, the script may take some time to fetch all exchange rates.

- **Data Accuracy**:

  - The script attempts to find the closest available exchange rate when the exact date is not present.
  - For precise financial calculations, consider verifying exchange rates independently.

- **Dependencies**:

  - Ensure you have the required Python packages installed.
  - You can install all dependencies using the provided `requirements.txt` file.

## Troubleshooting

- **Encountering Errors**:

  - If you receive errors about missing exchange rates or parsing dates, check your CSV files for correct formatting.
  - Ensure your transaction dates do not include future dates beyond the current date.

- **Graphical Output Issues**:

  - If the script fails to display graphs, ensure your environment supports graphical output.
  - For headless servers, you may need to adjust the script to save graphs to files instead of displaying them.

## Contributing

Contributions are welcome! Feel free to submit a pull request or open an issue to discuss improvements or report bugs.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- This script uses the [CoinGecko API](https://www.coingecko.com/en/api/documentation) for fetching historical cryptocurrency exchange rates.
- Localization is handled using the [Babel](https://babel.pocoo.org/en/latest/) library.
