import requests # type: ignore
from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv
from colorama import init, Fore, Style
init(autoreset=True)

# API Keys
load_dotenv()
weather_key = os.getenv("OPENWEATHER_API_KEY")
google_key = os.getenv("GOOGLE_API_KEY")
exchange_key = os.getenv("EXCHANGE_API_KEY")
unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")

def get_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_key}&units=metric"
    response = requests.get(url)
    data = response.json()

    if response.status_code == 200:
        offset = data["timezone"]  # seconds from UTC
        local_time = (datetime.utcnow() + timedelta(seconds=offset)).strftime('%Y-%m-%d %H:%M:%S')

        weather = {
            "description": data["weather"][0]["description"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "local_time": local_time,
            "country": data["sys"]["country"],
            "lat": data["coord"]["lat"],
            "lon": data["coord"]["lon"]
        }
        return weather
    else:
        return {"error": data.get("message", "Something went wrong.")}

def get_currency_code(country_code):
    # Simplified map; you can add more
    currency_map = {
        "US": "USD",
        "JP": "JPY",
        "FR": "EUR",
        "GB": "GBP",
        "CN": "CNY",
        "CA": "CAD",
        "AU": "AUD"
    }
    return currency_map.get(country_code.upper(), None)

def get_exchange_rate(from_currency="CAD", to_currency="USD"):
    url = f"https://v6.exchangerate-api.com/v6/{exchange_key}/pair/{from_currency}/{to_currency}"
    res = requests.get(url).json()
    if res["result"] == "success":
        return res["conversion_rate"]
    else:
        return None
    
def get_attractions(lat, lon):
    url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={lat},{lon}"
        f"&radius=5000"
        f"&type=tourist_attraction"
        f"&key={google_key}"
    )

    response = requests.get(url)
    data = response.json()
    if data.get("status") != "OK":
        print("Error message:", data.get("error_message", "No error message provided"))
        print("Full response:", data)
        return []


    places = []
    try:
        for place in data.get("results", [])[:5]:
            name = place.get("name", "Unknown")
            address = place.get("vicinity", "No address")
            maps_url = f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}"
            places.append(f"[{name}]({maps_url}) - {address}")


    except Exception as e:
        print("Error parsing Google Places data:", e)

    return places

def get_top_places(lat, lon, place_type, api_key):
    url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        f"?location={lat},{lon}"
        f"&radius=5000"
        f"&type={place_type}"
        f"&opennow=true"
        f"&key={api_key}"
    )
    response = requests.get(url)
    data = response.json()

    places = []
    if data.get("status") == "OK":
        for place in data.get("results", [])[:5]:
            name = place.get("name", "Unknown")
            address = place.get("vicinity", "No address")
            place_id = place.get("place_id", "")
            maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
            places.append(f"[{name}]({maps_url}) - {address}")
    return places

def init_db():
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_city TEXT,
                    destination TEXT,
                    temperature REAL,
                    currency_rate TEXT,
                    query_time TEXT
                )''')
    conn.commit()
    conn.close()

def save_query(user_city, destination, temperature, currency_rate):
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("INSERT INTO queries (user_city, destination, temperature, currency_rate, query_time) VALUES (?, ?, ?, ?, ?)", 
              (user_city, destination, temperature, currency_rate, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def show_history():
    conn = sqlite3.connect("travel.db")
    c = conn.cursor()
    c.execute("SELECT * FROM queries ORDER BY query_time DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("No history found.")
        return

    print("\n--- Travel Query History ---")
    for row in rows:
        print(f"ID: {row[0]} | From: {row[1]} | To: {row[2]} | Temp: {row[3]}°C | Rate: {row[4]} | Time: {row[5]}")

def get_city_image(city, api_key):
    url = f"https://api.unsplash.com/photos/random?query={city}&client_id={api_key}"
    response = requests.get(url)
    data = response.json()
    if response.status_code == 200 and "urls" in data:
        return data["urls"]["regular"]
    else:
        return None


# Main Program
init_db()
city = input("Enter a city for your trip: ")
weather_info = get_weather(city)

image_url = get_city_image(city, unsplash_key)
if image_url:
    print(f"\nCity Image for {city}: {image_url}")
else:
    print("No image found for this city.")

print(Fore.CYAN + "\n🌍 Travel Info 🌍")
if "error" in weather_info:
    print(Fore.RED + "❌ Error:", weather_info["error"])
else:
    print(Fore.YELLOW + f"📍 City: {city}")
    print(Fore.GREEN + f"🌤️ Weather: {weather_info['description']}")
    print(Fore.RED + f"🌡️ Temperature: {weather_info['temperature']}°C")
    print(Fore.LIGHTRED_EX + f"🥵 Feels Like: {weather_info['feels_like']}°C")
    print(Fore.MAGENTA + f"⌚ Local Time: {weather_info['local_time']}")

    print(Fore.BLUE + "\n🎯 Top 5 Places to Visit:")
    places = get_attractions(weather_info["lat"], weather_info["lon"])
    for i, place in enumerate(places, start=1):
        print(Fore.YELLOW + f"{i}. {place}")

    currency_code = get_currency_code(weather_info["country"])
    if currency_code:
        rate = get_exchange_rate("CAD", currency_code)
        if rate:
            print(Fore.GREEN + f"💱 Currency: 1 CAD = {rate:.2f} {currency_code}")
        else:
            print(Fore.RED + "💱 Currency: Rate unavailable.")


        user_city = input(Fore.CYAN + "🏠 Enter your current city (leave blank if same): ") or city
        save_query(user_city, city, weather_info["temperature"], f"1 CAD = {rate:.2f} {currency_code}")

        print(Fore.BLUE + "\n🏨 Top 5 Hotels:")
        hotels = get_top_places(weather_info["lat"], weather_info["lon"], "lodging", google_key)
        for i, hotel in enumerate(hotels, start=1):
            print(Fore.LIGHTBLUE_EX + f"{i}. {hotel}")

        print(Fore.BLUE + "\n🍽️ Top 5 Restaurants:")
        restaurants = get_top_places(weather_info["lat"], weather_info["lon"], "restaurant", google_key)
        for i, restaurant in enumerate(restaurants, start=1):
            print(Fore.LIGHTBLUE_EX + f"{i}. {restaurant}")
    else:
        print(Fore.RED + "⚠️ Currency data not available for this country.")

    show = input(Fore.CYAN + "\n📜 View your past travel queries? (yes/no): ").lower()
    if show == "yes":
        show_history()
