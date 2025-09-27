import os
import sys
import csv
import uuid
from flask import Flask, request, render_template_string, send_from_directory, after_this_request
from datetime import datetime

# Add the subdirectory to the Python path to allow imports from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '5paisa_strangle_trader'))

from historical_data import fetch_historical_data
import config

# Initialize the Flask app
app = Flask(__name__)

# --- Manual Template Loading ---
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
    csv_filename = None
    today = datetime.today().strftime('%Y-%m-%d')
    form_data = request.form

    if request.method == 'POST':
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
                    # Generate a unique filename and save the data to a temporary CSV file
                    csv_filename = f"data_{uuid.uuid4()}.csv"
                    tmp_filepath = os.path.join('tmp', csv_filename)

                    with open(tmp_filepath, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                        writer.writerows(candles)
                else:
                    error = "Failed to fetch data from the API or no data was returned. Check the console for more details."
            except KeyError as e:
                error = f"Missing form field: {e}"
            except Exception as e:
                error = f"An internal error occurred: {e}"

    template_string = load_template('index.html')
    return render_template_string(template_string, candles=candles, error=error, to_date=today, form_data=form_data, csv_filename=csv_filename)

@app.route('/download/<path:filename>')
def download(filename):
    """
    Securely sends a file from the 'tmp' directory for download
    and deletes it afterwards.
    """
    tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')

    # Schedule the file for deletion after the request has been handled
    @after_this_request
    def cleanup(response):
        try:
            os.remove(os.path.join(tmp_dir, filename))
        except Exception as e:
            app.logger.error(f"Error removing temporary file {filename}: {e}")
        return response

    # Use send_from_directory for security
    return send_from_directory(tmp_dir, filename, as_attachment=True)

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Access the dashboard at http://127.0.0.1:5000")
    # Turning debug=True is helpful for development
    app.run(host='0.0.0.0', port=5000, debug=True)