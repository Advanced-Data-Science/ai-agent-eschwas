import requests
import json
import logging

## API Demo: Fetching Cat Facts
# Set up logging configuration
logging.basicConfig(level=logging.INFO)

# Make your first API call to get a random cat fact
def get_five_cat_facts():
    url = "https://catfact.ninja/fact"
    facts = []
    
    for i in range(5):
        try:
            
            # Send GET request to the API
            fact = requests.get(url)
            
            # Check if request was successful
            if fact.status_code == 200:
                # Parse JSON response
                data = fact.json()
                facts.append(data['fact'])
                logging.info(f"Retrieved fact {i+1}")

            else:
               logging.error(f"Error: {fact.status_code}")

        except Exception as e:
            logging.exception("An error occurred while fetching a cat fact")

    return facts

# Get five cat facts
cat_facts = get_five_cat_facts()

# Print the cat facts
for i, fact in enumerate(cat_facts, 1):
    print(f"Fact {i}: {fact}")

# Save to JSON file
with open("cat_facts.json", "w") as f:
    json.dump(cat_facts, f, indent=4)





## Additional API example: Get public holidays for a specific country and year
# Using Nager.Date API (free, no key required)
import requests

def get_public_holidays(country_code="US", year=2024):
    """
    Get public holidays for a specific country and year
    Uses Nager.Date API (free, no key required)
    """
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{country_code}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an exception for bad status codes
        
        holidays = response.json()
        return holidays
    
    except requests.exceptions.RequestException as e:
        logging.error(f"[{country_code}] Request failed: {e}")
        return None

# Test with different countries
countries = ['US', 'CA', 'GB']
all_data = {}
for country in countries:
    holidays = get_public_holidays(country)
    if holidays:
        # Extract only date + name
        extracted = [{"date": h["date"], "name": h["name"]} for h in holidays]
        all_data[country] = extracted

        # Print the holidays
        print(f"\n{country} holidays in 2024:")
        for h in extracted:
            print(f"{h['date']} — {h['name']}")
    else:
        all_data[country] = []
        print(f"\n{country} holidays in 2024: No data.")

# Save extracted holidays to JSON
with open("holidays.json", "w") as f:
    json.dump(all_data, f, indent=4)

# Summary of holiday counts
print("\n=== Summary of Holiday Counts ===")
for country, holidays in all_data.items():
    print(f"{country}: {len(holidays)} holidays")

    '''
    I learned how to make API calls using requests in Python, how to write to JSON files, and how to handle errors and logging.
    A learned that making multiple API calls in a loop is straightforward, and I can extract and format data as needed. Looping through
    different countries as this example shows how easy it is to scale API calls for different parameters. I also learned that some APIs
    take a parameterized URL structure, which is useful for customizing requests in order to get desired data. Overall, this what a great
    exercise to understand the basics of working with APIs in Python. I'll definitely be using these techniques in future projects.
    '''
