# This script will contain the Flask web server for the historical data dashboard.
import os
from flask import Flask, render_template, request
from historical_data import fetch_historical_data
import config
from datetime import datetime

# --- Robust Path for Templates ---
# Get the absolute path of the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Join this path with the 'templates' folder name
template_folder = os.path.join(script_dir, 'templates')

# Initialize the Flask app with the explicit template folder path
app = Flask(__name__, template_folder=template_folder)

@app.route('/', methods=['GET', 'POST'])
def index():
    candles = None
    error = None

    # Set default dates for the form
    today = datetime.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        # Check for valid access token first
        if config.ACCESS_TOKEN == "YOUR_ACCESS_TOKEN" or not config.ACCESS_TOKEN:
            error = "Access token not found in config.py. Please run an authentication script first."
            return render_template('index.html', error=error, to_date=today)

        try:
            # Get form data
            exch = request.form['exch']
            exch_type = request.form['exch_type']
            scrip_code = request.form['scrip_code']
            interval = request.form['interval']
            from_date = request.form['from_date']
            to_date = request.form['to_date']

            # Fetch the data
            candles = fetch_historical_data(exch, exch_type, scrip_code, interval, from_date, to_date)

            if candles is None:
                error = "Failed to fetch data from the API. Check the console for more details."

        except Exception as e:
            error = f"An internal error occurred: {e}"

        return render_template('index.html', candles=candles, error=error, to_date=today)

    # For GET request, just show the form
    return render_template('index.html', to_date=today)

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Access the dashboard at http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000)