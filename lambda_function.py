import json
import os
from urllib.request import Request, urlopen

from warhorn_lambda.methods import submit_warhorn, get_submissions

token = os.environ['user_access_token']  # token to access warhorn api
sheet_id = os.environ['sheet_id']  # public google sheet id with submissions
event_str = os.environ["warhorn_event"] # string representing warhorn event

def lambda_handler(event, context):

    with open("warhorn_queries.json") as file:
        warhorn_queries =json.load(file)

    req = Request("https://warhorn.net/graphql", method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header("Authorization", "bearer " + token)