import requests
import json

# Make your first API call to get a random cat fact
def get_five_cat_facts():
    url = "https://catfact.ninja/fact"
    facts = []
    
    try:
        for _ in range(5):

            # Send GET request to the API
            fact = requests.get(url)
        
            # Check if request was successful
            if fact.status_code == 200:
                # Parse JSON response
                data = fact.json()
                facts.append(data['fact'])
            else:
                print(f"Error: {fact.status_code}")
                return None
        
        return facts
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Test your function
cat_facts = get_five_cat_facts()
print(f"Cat facts: {cat_facts}")
