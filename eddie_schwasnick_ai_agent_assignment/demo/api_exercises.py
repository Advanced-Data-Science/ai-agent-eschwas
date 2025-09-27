import requests
import json
import logging

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
