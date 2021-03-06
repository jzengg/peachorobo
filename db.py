import json

JSON_PATH = "data/db.json"


def get_mystery_dinners():
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    return data


def create_mystery_dinner(pairings):
    dinners = get_mystery_dinners()
    dinners.append(pairings)
    with open(JSON_PATH, 'w') as f:
        json.dump(dinners, f)

create_mystery_dinner(['test'])
print(get_mystery_dinners())
