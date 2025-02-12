from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Replace with your actual, valid OpenWeatherMap API key.
OPENWEATHER_API_KEY = "e88526da16565ae7583c67ed7da6fd7e"

def get_crime_date():
    # Hard-code the crime data date.
    return "2024-12"

def get_crime_data(lat, lon, crime_date):
    """
    Fetches crime data using the crimes-at-location endpoint from data.police.uk.
    """
    crime_url = f"https://data.police.uk/api/crimes-at-location?date={crime_date}&lat={lat}&lng={lon}"
    print(f"DEBUG: Requesting crime data from: {crime_url}")
    try:
        crime_response = requests.get(crime_url)
    except Exception as e:
        print("ERROR: Exception during crime data request:", e)
        return {"error": "Unable to retrieve crime data."}
    
    print(f"DEBUG: Crime data response status: {crime_response.status_code}")
    if crime_response.status_code == 502:
        return {"error": "Bad Gateway: The police data is currently unavailable. Please try again later."}
    elif crime_response.status_code != 200:
        return {"error": f"Crime data is not available. Status code: {crime_response.status_code}"}
    
    try:
        crimes = crime_response.json()
    except Exception as e:
        print("ERROR: Exception parsing crime data JSON:", e)
        return {"error": "Failed to parse crime data."}
    
    print("DEBUG: Crime data JSON response:", crimes)
    total_crimes = len(crimes)
    breakdown = {}
    crime_details = []
    for crime in crimes:
        category = crime.get("category", "unknown")
        breakdown[category] = breakdown.get(category, 0) + 1
        
        street_name = crime.get("location", {}).get("street", {}).get("name", "Unknown")
        latitude = crime.get("location", {}).get("latitude", "N/A")
        longitude = crime.get("location", {}).get("longitude", "N/A")
        month = crime.get("month", "N/A")
        outcome_status = crime.get("outcome_status")
        if outcome_status:
            outcome_category = outcome_status.get("category", "No outcome")
            outcome_date = outcome_status.get("date", "")
            outcome = f"{outcome_category} ({outcome_date})" if outcome_date else outcome_category
        else:
            outcome = "No outcome"
        
        detail = {
            "id": crime.get("id"),
            "persistent_id": crime.get("persistent_id"),
            "category": category,
            "month": month,
            "street": street_name,
            "latitude": latitude,
            "longitude": longitude,
            "outcome": outcome
        }
        crime_details.append(detail)
    
    return {"total": total_crimes, "breakdown": breakdown, "crime_details": crime_details}

def get_data(postcode):
    """
    Fetches real‑time data for a given full postcode.
    """
    print(f"DEBUG: Starting get_data for postcode: {postcode}")
    
    postcode = postcode.strip()
    print(f"DEBUG: Trimmed postcode: '{postcode}'")
    
    if " " not in postcode:
        raise Exception("Please enter a full postcode (e.g., 'SW1A 1AA').")
    
    postcode_clean = postcode.replace(" ", "")
    if len(postcode_clean) < 5:
        raise Exception("The provided postcode appears to be incomplete. Please enter a full postcode (e.g., 'SW1A 1AA').")
    
    pc_url = f"https://api.postcodes.io/postcodes/{postcode_clean}"
    print(f"DEBUG: Requesting location data from: {pc_url}")
    pc_response = requests.get(pc_url)
    print(f"DEBUG: postcodes.io response status: {pc_response.status_code}")
    if pc_response.status_code != 200:
        raise Exception("Failed to get location data. Status code: " + str(pc_response.status_code))
    
    try:
        pc_json = pc_response.json()
    except Exception as e:
        raise Exception("Failed to parse location data JSON.")
    
    print("DEBUG: postcodes.io JSON response:", pc_json)
    if pc_json.get("status") != 200 or not pc_json.get("result"):
        raise Exception("Invalid postcode or no location data found. Please ensure you provide a full postcode (e.g., 'SW1A 1AA').")
    
    lat = pc_json["result"]["latitude"]
    lon = pc_json["result"]["longitude"]
    country = pc_json["result"].get("country", "Unknown")
    print(f"DEBUG: Retrieved latitude: {lat}, longitude: {lon}, country: {country}")
    
    weather_url = (
        f"https://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
    )
    print(f"DEBUG: Requesting weather data from: {weather_url}")
    try:
        weather_response = requests.get(weather_url)
    except Exception as e:
        raise Exception("Unable to retrieve weather data.")
    
    print(f"DEBUG: OpenWeatherMap response status: {weather_response.status_code}")
    if weather_response.status_code != 200:
        raise Exception("Unable to retrieve weather data. Status code: " + str(weather_response.status_code))
    
    try:
        w = weather_response.json()
    except Exception as e:
        raise Exception("Failed to parse weather data JSON.")
    
    print("DEBUG: OpenWeatherMap JSON response:", w)
    weather_data = {
        "temperature": f"{w['main']['temp']}°C",
        "condition": w['weather'][0]['description'].capitalize(),
        "icon": w['weather'][0]['icon']
    }
    
    crime_date = get_crime_date()
    print(f"DEBUG: Using crime data date: {crime_date}")
    crime_data = get_crime_data(lat, lon, crime_date)
    
    data = {
        "postcode": postcode.upper(),
        "lat": lat,
        "lon": lon,
        "country": country,
        "weather": weather_data,
        "crime": crime_data
    }
    print("DEBUG: Final combined data:", data)
    return data

@app.route("/api/<postcode>", methods=["GET"])
def api_data(postcode):
    try:
        data = get_data(postcode)
        return jsonify(data)
    except Exception as e:
        print("ERROR: In api_data route:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # This block is used for development.
    # In production, run Gunicorn with:
    #   gunicorn app:app
    app.run(debug=True, port=5000)
