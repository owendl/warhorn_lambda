import json
import os
from urllib.request import Request, urlopen

from warhorn_lambda.methods import main

token = os.environ['user_access_token']  # token to access warhorn api
sheet_id = os.environ['sheet_id']  # public google sheet id with submissions
event_str = os.environ["warhorn_event"] # string representing warhorn event

with open("warhorn_queries.json") as file:
    warhorn_queries =json.load(file)
    
with open("col_rename.json") as file:
    col_rename = json.load(file)

def lambda_handler(event, context):
    completed_entries, error_list, dropped_records = main(token, sheet_id, event_str, warhorn_queries, col_rename)
    return json.dumps({"completed":len(completed_entries),"missing_data":dropped_records,"errored":error_list})