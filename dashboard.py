import os
import sys
import io
import csv
from flask import Flask, request, render_template_string, session, Response
from datetime import datetime

# Add the subdirectory to the Python path to allow imports from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '5paisa_strangle_trader'))

from historical_data import fetch_historical_data
import config

# Initialize the Flask app
app = Flask(__name__)
# Set a secret key for session management. Required for storing data.
app.secret_key = os.urandom(24)

# --- Manual Template Loading ---
# This is a robust workaround for environments where template discovery fails.
def load_template(filename):
    try:
        template_path = os.path.join(os.path.dirname(__file__), 'templates', filename)
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return f"<h1>Error</h1><p>Template '{filename}' not found at '{template_path}'.</p>"

@app.route('/', methods=['GET', 'POST'])
def index():
    candles = None
    error = None
    today = datetime.today().strftime('%Y-%m-%d')
    form_data = request.form

    if request.method == 'POST':
        # Clear any previous data from the session on a new request
        session.pop('candles', None)

        if config.ACCESS_TOKEN == "YOUR_ACCESS_TOKEN" or not config.ACCESS_TOKEN:
            error = "Access token not found in config.py. Please run an authentication script first."
        else:
            try:
                exch, exch_type, scrip_code, interval, from_date, to_date = (
                    form_data['exch'], form_data['exch_type'], form_data['scrip_code'],
                    form_data['interval'], form_data['from_date'], form_data['to_date']
                )
                candles = fetch_historical_data(exch, exch_type, scrip_code, interval, from_date, to_date)
                if candles:
                    # Store the fetched data in the session for the download link
                    session['candles'] = candles
                else:
                    error = "Failed to fetch data from the API or no data was returned. Check the console for more details."
            except KeyError as e:
                error = f"Missing form field: {e}"
            except Exception as e:
                error = f"An internal error occurred: {e}"

    # Manually load the template and render it as a string
    template_string = load_template('index.html')
    return render_template_string(template_string, candles=candles, error=error, to_date=today, form_data=form_data)

@app.route('/download_csv')
def download_csv():
    # Retrieve the candle data from the session
    candles = session.get('candles')

    if not candles:
        return "No data to download. Please fetch data first.", 404

    # Use an in-memory text buffer to build the CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Write the header row
    header = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    writer.writerow(header)

    # Write the data rows
    writer.writerows(candles)

    # Prepare the response
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=historical_data.csv"}
    )

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Access the dashboard at http://127.0.0.1:5000")
    # Turning debug=True is helpful for development
    app.run(host='0.0.0.0', port=5000, debug=True)