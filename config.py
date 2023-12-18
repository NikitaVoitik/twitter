import json

settings = dict()


def options():
    with open('config.json') as file:
        json_data = json.load(file)['account_lifestyle']
    global settings
    settings = json_data
