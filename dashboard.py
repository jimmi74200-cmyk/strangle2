import os
import sys
from flask import Flask, render_template, request
from datetime import datetime

# Add the subdirectory to the Python path to allow imports from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '5paisa_strangle_trader'))

from historical_data import fetch_historical_data
import config

# Initialize the Flask app. It will automatically find the 'templates' folder
# in the same directory (the project root).
app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    candles = None
    error = None

    # Set default dates for the form
    today = datetime.today().strftime('%Y-%m-%d')

    # Use request.form to repopulate the form after submission
    form_data = request.form

    if request.method == 'POST':
        # Check for valid access token first
        if config.ACCESS_TOKEN == "YOUR_ACCESS_TOKEN" or not config.ACCESS_TOKEN:
            error = "Access token not found in config.py. Please run an authentication script first."
        else:
            try:
                # Get form data
                exch = form_data['exch']
                exch_type = form_data['exch_type']
                scrip_code = form_data['scrip_code']
                interval = form_data['interval']
                from_date = form_data['from_date']
                to_date = form_data['to_date']

                # Fetch the data
                candles = fetch_historical_data(exch, exch_type, scrip_code, interval, from_date, to_date)

                if candles is None:
                    error = "Failed to fetch data from the API. Check the console for more details."

            except KeyError as e:
                error = f"Missing form field: {e}"
            except Exception as e:
                error = f"An internal error occurred: {e}"

    return render_template('index.html', candles=candles, error=error, to_date=today, form_data=form_data)

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Access the dashboard at http://127.0.0.1:5000")
    # Turning debug=True is helpful for development
    app.run(host='0.0.0.0', port=5000, debug=True)