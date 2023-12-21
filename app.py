from flask import send_file,Flask, render_template, request, redirect, url_for, session
from passlib.hash import sha256_crypt
import psycopg2
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import io
import matplotlib
matplotlib.use('Agg')
from decimal import Decimal

app = Flask(__name__, template_folder='templates')
app.secret_key = '67'  # Change this to a secure random key

# Configure the PostgreSQL database
db_config = {
    'host': 'localhost',
    'port': '5432',
    'user': 'postgres',
    'password': 'Piyush@2018',
    'database': 'postgres',
}

# Function to execute SQL queries
def execute_query(query, params=None, fetch_all=True):
    connection = None
    cursor = None
    result = None

    try:
        connection = psycopg2.connect(**db_config)
        
        print(connection)
        cursor = connection.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        connection.commit()
        

        if fetch_all:
            try:
                result = cursor.fetchall()
                
            except psycopg2.ProgrammingError:
                pass  # Ignore errors when trying to fetch results from DDL queries

    except psycopg2.Error as e:
        print(f"Error executing query: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return result


# Create tables if they don't exist
create_tables_query = """
    CREATE TABLE IF NOT EXISTS users (
        customerid SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL
    );
     
    CREATE TABLE IF NOT EXISTS devicemodel (
        modelid SERIAL PRIMARY KEY,
        type VARCHAR(50),
        modelnumber VARCHAR(50)
    );

    CREATE TABLE IF NOT EXISTS device (
        deviceid SERIAL PRIMARY KEY,
        locationid INT,
        modelid INT,
        FOREIGN KEY (locationid) REFERENCES service_location(locationid),
        FOREIGN KEY (modelid) REFERENCES devicemodel(modelid)
    );
"""

execute_query(create_tables_query)

# Home page redirects to the login page
@app.route('/')
def index():
    return redirect(url_for('login'))
# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Initialize error as None

    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        # Fetch user data
        user_query = "SELECT customerid, password FROM users WHERE username = %s"
        user_data = execute_query(user_query, (username,))

        if not user_data:
            error = 'Invalid login'  # Set the error message
        else:
            customer_id, plain_text_password = user_data[0]

            # Verify plain text password
            if password_candidate == plain_text_password:
                session['logged_in'] = True
                session['username'] = username
                session['customer_id'] = customer_id

                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'  # Set the error message

    return render_template('login.html', error=error)
 # Pass the error variable to the template

# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        billing_address = request.form['billing_address']

        # Check if the username is already taken
        check_query = "SELECT COUNT(*) FROM users WHERE username = %s"
        result = execute_query(check_query, (username,), fetch_all=False)

        if result and result[0][0] > 0:
            return render_template('register.html', error='Username already taken')

        # Insert into users table
        user_insert_query = "INSERT INTO users (username, password) VALUES (%s, %s)"
        execute_query(user_insert_query, (username, password))

        # Insert into customers table
        customer_insert_query = "INSERT INTO customer (name, billingaddress) VALUES (%s, %s)"
        execute_query(customer_insert_query, (name, billing_address))

        # Fetch the newly created customerid
        fetch_id_query = "SELECT customerid FROM users WHERE username = %s"
        customer_id_result = execute_query(fetch_id_query, (username,))

        if customer_id_result:
            customer_id = customer_id_result[0][0]
            session['logged_in'] = True
            session['username'] = username
            session['customer_id'] = customer_id

            return redirect(url_for('dashboard'))
        else:
            return render_template('register.html', error='Registration failed. Please try again.')

    return render_template('register.html')



# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        try:
            # Fetch user-specific data
            customer_id = session['customer_id']

            # Fetch service locations
            service_locations_query = "SELECT * FROM servicelocation WHERE customerid = %s"
            service_locations = execute_query(service_locations_query, (customer_id,))
            
            # Fetch devices
            devices_query = """
            SELECT device.deviceid, servicelocation.locationid, devicemodel.type, devicemodel.modelnumber
            FROM device
            JOIN devicemodel ON device.modelid = devicemodel.modelid
            JOIN servicelocation ON device.locationid = servicelocation.locationid
            WHERE servicelocation.customerid = %s
            """

            devices = execute_query(devices_query, (customer_id,))
            #print(devices)
            return render_template('dashboard.html', service_locations=service_locations, devices=devices)
        except Exception as e:
            print(f"Error fetching data from the database: {e}")
            # You can customize the error message or redirect to an error page.
            return render_template('error.html', error_message="An error occurred while fetching data.")
    else:
        return redirect(url_for('login'))
@app.route('/logout')
def logout():
    session.clear()  # Clear the session data
    return redirect(url_for('login'))  
@app.route('/add_service_location', methods=['GET', 'POST'])
def add_service_location():
    if 'logged_in' in session:
        if request.method == 'POST':
            # Process the form data
            address = request.form['address']
            unitnumber = request.form['unitnumber']
            moveindate = request.form['moveindate']
            squarefootage = request.form['squarefootage']
            bedrooms = request.form['bedrooms']
            occupants = request.form['occupants']
            zipcode = request.form['zipcode']

            # Validate the zipcode
            if not zipcode.isdigit():
                # If zipcode is not numeric, return an error message
                return render_template('add_service_location.html', error='Invalid zipcode')

            # Insert the data into the servicelocation table
            service_location_query = """
                INSERT INTO servicelocation
                (customerid, address, unitnumber, moveindate, squarefootage, bedrooms, occupants, zipcode)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            execute_query(service_location_query, (session['customer_id'], address, unitnumber, moveindate, squarefootage, bedrooms, occupants, zipcode))

            return redirect(url_for('dashboard'))

        else:
            # GET request, just render the form
            return render_template('add_service_location.html')

    else:
        return redirect(url_for('login'))




from flask import render_template, request, redirect, url_for, session


@app.route('/add_device_step1', methods=['GET', 'POST'])
def add_device_step1():
    if 'logged_in' in session:
        if request.method == 'GET':
            # Fetch service locations for the current user
            customer_id = session['customer_id']
            service_locations_query = "SELECT * FROM servicelocation WHERE customerid = %s"
            service_locations = execute_query(service_locations_query, (customer_id,))

            try:
                # Fetch device models for the dropdown menu
                device_models_query = "SELECT modelid, type, modelnumber FROM devicemodel"
                device_models = execute_query(device_models_query)

            except Exception as e:
                print(f"Error fetching device models: {e}")
                device_models = []

            return render_template('add_device_step1.html', service_locations=service_locations, device_models=device_models)

        elif request.method == 'POST':
            # Get form data
            selected_service_location = request.form['service_location']
            selected_device_type = request.form['device_type']

            # Fetch model numbers based on the selected device type
            model_numbers_query = "SELECT modelnumber FROM devicemodel WHERE type = %s"
            model_numbers = execute_query(model_numbers_query, (selected_device_type,))

            return render_template('add_device_step2.html', model_numbers=model_numbers,
                                   selected_service_location=selected_service_location,
                                   selected_device_type=selected_device_type)

    else:
        return redirect(url_for('login'))

@app.route('/add_device_step2', methods=['POST'])
def add_device_step2():
    if 'logged_in' in session:
        if request.method == 'POST':
            # Get form data
            service_location_id = request.form['service_location']
            device_type = request.form['device_type']
            model_number = request.form['model_number']
            model_number_1 = clean_string(model_number)
            print(type(model_number))
            
            try:
                # Debug information
                print("Device Type:", device_type)
                print("Model Number:", model_number_1)

                # Fetch the model id based on the selected device type and model number
                model_id_query = "SELECT modelid FROM devicemodel WHERE type = %s AND modelnumber = %s"
                print("Model ID Query:", model_id_query)
                model_id_result = execute_query(model_id_query, (device_type, model_number_1))
                print(model_id_result)

                if model_id_result:
                    model_id = model_id_result[0][0]

                    # Perform the database insertion for the new device
                    insert_device_query = "INSERT INTO device (locationid, modelid) VALUES (%s, %s)"
                    execute_query(insert_device_query, (service_location_id, model_id))

                    # Redirect back to the dashboard or wherever you'd like
                    return redirect(url_for('dashboard'))
                else:
                    print("No model ID found for the selected type and model number.")

            except Exception as e:
                print(f"Error inserting device: {e}")
                # Print or log the specific error message for further investigation

        else:
            print("Invalid request method")  # Log or print the invalid method for further investigation

        # Handle the case where there's an error or an invalid request method
        return redirect(url_for('dashboard'))

    else:
        return redirect(url_for('login'))

import re

def clean_string(text):
  pattern = r"[^\w\s]"
  return re.sub(pattern, "", text)

from flask import request    

@app.route('/energy_consumption_form', methods=['GET'])
def energy_consumption_form():
    if 'logged_in' in session:
        return render_template('energy_consumption_form.html')
    else:
        return redirect(url_for('login'))
def get_user_locations():
    customer_id = session['customer_id']
    user_locations_query = "SELECT locationid FROM servicelocation WHERE customerid = %s"
    user_locations = [location_id for location_id in execute_query(user_locations_query, (customer_id,))]
    return user_locations

@app.route('/energy_consumption_graph', methods=['POST'])
def energy_consumption_graph():
    if 'logged_in' in session:
        try:
            location_id = int(request.form.get('location_id'))
            print(location_id)
            # Verify that the user owns the requested location
            user_locations = get_user_locations()
            
            if (location_id,) not in user_locations:
                raise ValueError(f"User doesn't have access to location {location_id}")

            # Fetch total energy consumption data for the specified location ID
            energy_data_query = """
                SELECT to_char(ed.timestamp, 'Mon YYYY') AS month_year, SUM(ed.value) AS total_consumption
                FROM EnergyData ed
                INNER JOIN Device d ON d.DeviceID = ed.DeviceID
                INNER JOIN ServiceLocation sl ON sl.LocationID = d.LocationID
                WHERE sl.LocationID = %s
                AND ed.EventLabel = 'energy use'
                GROUP BY to_char(ed.timestamp, 'Mon YYYY')
                ORDER BY to_char(ed.timestamp, 'Mon YYYY');
            """
            energy_data = execute_query(energy_data_query, (location_id,))
            print(f"Fetched data: {energy_data}")

            if energy_data is None:
                raise ValueError(f"No data found for Location ID {location_id}")

            # Extract data for the graph
            months = []
            total_consumption = []
            for entry in energy_data:
             month, consumption = entry
             months.append(month)
             total_consumption.append(consumption)

            # Generate the bar graph using matplotlib
            plt.figure(figsize=(8, 6))
            plt.bar(months, total_consumption, color='blue')
            plt.xlabel('Month (Year)')
            plt.ylabel('Total Energy Consumption')
            plt.title(f'Total Energy Consumption Graph for Location {location_id}')
            plt.grid(True)
            plt.tight_layout()
            plt.xticks(range(len(months)), months)

            # Save the plot to a bytes buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()

            # Move the buffer cursor to the beginning
            buffer.seek(0)

            # Send the buffer as a response
            return send_file(buffer, mimetype='image/png', download_name='energy_consumption_plot.png')
        except Exception as e:
            print(f"Error processing /energy_consumption_graph: {e}")
            return render_template('error.html', error_message=f"An error occurred: {e}")
    else:
        return redirect(url_for('login'))

@app.route('/energy_consumption_form_24_hours', methods=['GET'])
def energy_consumption_form_24_hours():
    if 'logged_in' in session:
        return render_template('energy_consumption_form_24_hours.html')
    else:
        return redirect(url_for('login'))


@app.route('/energy_consumption_graph_24_hours', methods=['POST'])
def energy_consumption_graph_24_hours():
    if 'logged_in' in session:
        try:
            location_id = int(request.form.get('location_id'))
            timeframe = 'last_24_hours'

            # Verify that the user owns the requested location
            
            print(location_id)
            # Verify that the user owns the requested location
            user_locations = get_user_locations()
            
            if (location_id,) not in user_locations:
                raise ValueError(f"User doesn't have access to location {location_id}")

            # Build the energy data query based on the timeframe
            if timeframe == 'last_24_hours':
                timeframe_query = """
                    SELECT
                        DATE_TRUNC('hour', ed.timestamp) AS hour,
                        SUM(ed.value) AS total_consumption
                    FROM EnergyData ed
                    INNER JOIN Device d ON d.DeviceID = ed.DeviceID
                    INNER JOIN ServiceLocation sl ON sl.LocationID = d.LocationID
                    WHERE sl.LocationID = %s
                    AND ed.timestamp BETWEEN CURRENT_TIMESTAMP - INTERVAL '24 hours' AND CURRENT_TIMESTAMP
                    AND ed.EventLabel = 'energy use'
                    GROUP BY DATE_TRUNC('hour', ed.timestamp)
                    ORDER BY DATE_TRUNC('hour', ed.timestamp);
                """
            else:
                # Handle other timeframes (e.g., last_week, last_month)
                raise NotImplementedError(f"Timeframe '{timeframe}' is not supported yet")

            # Fetch energy data
            energy_data = execute_query(timeframe_query, (location_id,))
            

            if energy_data is None:
                raise ValueError(f"No data found for Location ID {location_id} and timeframe '{timeframe}'")

            # Extract data for the graph
            hours = []
            total_consumption = []
            for entry in energy_data:
                hour, consumption = entry

                if hour in hours:
        # Update existing entry directly
                   index = hours.index(hour)
                   total_consumption[index] += Decimal(consumption)
                else:
        # Append only if the hour doesn't exist
                    hours.append(hour)
                    total_consumption.append(Decimal(consumption))

            print(hours)
            print(total_consumption)
            formatted_hours = [hour.strftime('%H:%M') for hour in hours]
            # Generate the energy vs. hours graph
            plt.figure(figsize=(14, 12))
            plt.plot(formatted_hours, total_consumption, color='blue')
            plt.xlabel('Hour of Day')
            plt.ylabel('Total Energy Consumption')
            plt.title(f'Energy Consumption in the last 24 hours for Location {location_id}')
            plt.grid(True)
            plt.xticks(rotation=45)

            # Save the plot to a bytes buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()

            # Move the buffer cursor to the beginning
            buffer.seek(0)

            # Send the buffer as a response
            return send_file(buffer, mimetype='image/png', download_name='energy_consumption_plot.png')
        except Exception as e:
            print(f"Error processing /energy_consumption_graph: {e}")
            return render_template('error.html', error_message=f"An error occurred: {e}")
    else:
        return redirect(url_for('login'))


@app.route('/average_for_a_month', methods=['GET'])
def average_for_a_month():
    if 'logged_in' in session:
        return render_template('average_for_a_month_form.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/generate_average_graph', methods=['POST'])
def generate_average_graph():
    try:
        # Replace this with your actual logic to fetch data
        location_id = int(request.form.get('location_id'))
        month = int(request.form.get('month'))
        year = int(request.form.get('year'))
        print (year)
        user_locations = get_user_locations()
            
        if (location_id,) not in user_locations:
                raise ValueError(f"User doesn't have access to location {location_id}")
        # Fetch data from the database
        query = """
            WITH TotEnergy AS (
        SELECT
        sl.LocationID,
        SUM(ed.Value) AS TotalEnergy
        FROM
        ServiceLocation sl
        JOIN Device d ON sl.LocationID = d.LocationID
        JOIN EnergyData ed ON d.DeviceID = ed.DeviceID
        WHERE
        EXTRACT(MONTH FROM ed.Timestamp) = %s
        AND EXTRACT(YEAR FROM ed.Timestamp) = %s
        AND ed.EventLabel = 'energy use'
        GROUP BY
        sl.LocationID
        ),
        SquareFootageAvg AS (
        SELECT
        sl.LocationID,
        sl.SquareFootage,
        AVG(ae.TotalEnergy) OVER (PARTITION BY sl.SquareFootage) AS AvgTotalEnergy
        FROM
        ServiceLocation sl
        JOIN TotEnergy ae ON sl.LocationID = ae.LocationID
        )
        SELECT
        sl.LocationID,
        sl.SquareFootage,
        ae.TotalEnergy AS MonthTotalEnergy,
        sfa.AvgTotalEnergy,
        CASE
        WHEN sl.SquareFootage BETWEEN sfa.SquareFootage * 0.95 AND sfa.SquareFootage * 1.05 THEN
            (ae.TotalEnergy / NULLIF(sfa.AvgTotalEnergy, 0)) * 100
        ELSE
            NULL
        END AS Percentage
        FROM
        ServiceLocation sl
        JOIN TotEnergy ae ON sl.LocationID = ae.LocationID
        JOIN SquareFootageAvg sfa ON sl.LocationID = sfa.LocationID
        WHERE
        sl.LocationID = %s;
        """
        params = (month, year, location_id)
        result = execute_query(query, params)
        print(result)
        # Process the result and generate the graph
        if result:
            location_ids, square_footages, total_energies, avg_total_energies, percentages = zip(*result)

            # Generate the graph
            plt.figure(figsize=(12, 8))
            # plt.bar(location_ids, total_energies, label='Location Consumption', color='none', edgecolor='red', linewidth=2)
            # plt.bar(location_ids, avg_total_energies, label='Average Consumption', color='none', edgecolor='blue', linewidth=2, linestyle='--')

            print(total_energies, type(total_energies))

            x_axis = ["Total Energy", "Total Average Energy"]
            y_axis = [total_energies[0], avg_total_energies[0]]

            plt.bar(x_axis, y_axis, color='maroon', width=0.2)

     
            plt.xlabel('Type of Energies')
            plt.ylabel('Energy Consumption')
            plt.title(f'Energy Consumption Comparison for Location {location_id} in {month}/{year}')
            plt.legend()
            plt.grid(True)
            # plt.xticks([])

            plt.show()

            # Save the plot to a bytes buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            plt.close()

            # Move the buffer cursor to the beginning
            buffer.seek(0)

            # Send the buffer as a response
            return send_file(buffer, mimetype='image/png', download_name='average_consumption_plot.png')
        else:
            return render_template('error.html', error_message=f"No data found for Location ID {location_id}")

    except Exception as e:
        print(f"Error processing /generate_average_graph: {e}")
        return render_template('error.html', error_message=f"An error occurred: {e}")

@app.route('/energy_cost_graph_form', methods=['GET'])
def energy_cost_graph_form():
    if 'logged_in' not in session:
        # Redirect to login page if the user is not logged in
        return redirect(url_for('login'))

    # Render the form for the energy cost graph
    return render_template('energy_cost_graph_form.html')

@app.route('/energy_cost_graph', methods=['POST'])
def energy_cost_graph():
    if 'logged_in' not in session:
        # Redirect to login page or handle the case where the user is not logged in
        return redirect(url_for('login'))

    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    customer_id = session['customer_id']  # Get customer_id from session

    query = """
        SELECT SL.locationid AS LocationId,
            SUM(COALESCE(E.value * ZEP.price, 0)) AS TotalEnergyCost,
            SUM(E.value) AS TotalEnergyUsage
        FROM ServiceLocation SL
        JOIN device ED ON SL.locationid = ED.locationid
        JOIN energydata E ON ED.deviceid = E.deviceid
        JOIN energyprice ZEP ON SL.zipcode = ZEP.zipcode
            AND E.timestamp >= ZEP.timestamp
            AND E.timestamp < ZEP.timestamp + INTERVAL '1 hours'
        WHERE E.timestamp >= %s AND E.timestamp < %s
        AND E.eventlabel = 'energy use' AND SL.customerid = %s
        GROUP BY SL.locationid;
    """

    data = execute_query(query, (start_date, end_date, customer_id))
    locations = [item[0] for item in data]
    total_costs = [item[1] for item in data]
    total_usage = [item[2] for item in data]

    # Plot for Total Energy Usage
    plt.figure(figsize=(10, 6))
    plt.bar(locations, total_usage, color='blue', label='Total Energy Usage')
    plt.xlabel('Location ID')
    plt.ylabel('Total Energy Usage')
    plt.title('Total Energy Usage per Location')
    plt.xticks(locations)
    plt.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    usage_image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    # Plot for Total Energy Cost
    plt.figure(figsize=(10, 6))
    plt.bar(locations, total_costs, color='green', label='Total Energy Cost')
    plt.xlabel('Location ID')
    plt.ylabel('Total Energy Cost')
    plt.title('Total Energy Cost per Location')
    plt.xticks(locations)
    plt.legend()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    cost_image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template('energy_cost_graph_display.html', usage_image=usage_image_base64, cost_image=cost_image_base64)

device_threads = {}

@app.route('/switch_on', methods=['GET'])
def switch_on():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    customer_id = session['customer_id']

    # Query to get enrolled devices for the logged-in customer
    query = """
        SELECT D.deviceid, D.locationid, DM.type, DM.modelnumber
        FROM Device D
        JOIN DeviceModel DM ON D.modelid = DM.modelid
        JOIN ServiceLocation SL ON D.locationid = SL.locationid
        WHERE SL.customerid = %s
    """
    devices = execute_query(query, (customer_id,))

    return render_template('switch_on.html', devices=devices)

import time
import random

def add_energy_data(device_id, interval=300):
    print(f"Current device threads status: {device_threads}")
    while True:
        time.sleep(interval)
        if not device_threads.get(device_id, {}).get('active', False):
            print(f"Thread for device {device_id} is not active")
            break  # Stop the loop if the device is not active
        # Generate a random value between 0.1 and 0.3
        random_value = round(random.uniform(0.1, 0.3), 2)

        # Insert data into EnergyData table
        query = """
            INSERT INTO EnergyData (deviceid, timestamp, eventlabel, value)
            VALUES (%s, NOW(), 'energy use', %s)
        """
        execute_query(query, (device_id, random_value))

        print(f"Added energy data for device {device_id}: {random_value}")
        time.sleep(interval)

from threading import Thread

@app.route('/switch_on_device', methods=['POST'])
def switch_on_device():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    device_id = request.form.get('device_id')

    # Update the thread entry before starting the thread
    if device_id not in device_threads or not device_threads[device_id]['thread'].is_alive():
        # Create the thread but don't start it yet
        thread = Thread(target=add_energy_data, args=(device_id,))
        thread.daemon = True

        # Update the dictionary entry
        device_threads[device_id] = {'thread': thread, 'active': True}

        # Now start the thread
        thread.start()
    else:
        # Reactivate the existing thread
        device_threads[device_id]['active'] = True

    return redirect(url_for('dashboard'))

@app.route('/switch_off', methods=['GET'])
def switch_off():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    return render_template('switch_off.html')

@app.route('/switch_off_device', methods=['POST'])
def switch_off_device():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    device_id = request.form.get('device_id')
    
    # Set the device's thread to inactive
    if device_id in device_threads:
        device_threads[device_id]['active'] = False

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
