import os
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
# from urllib.parse
import pandas as pd
import json


def get_submissions(sheet_id):
    SHEET_ID = sheet_id
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv'
    df = pd.read_csv(url)
    return df


def submit_warhorn(req, step= "me" ,query="{me{id,name}}", vars = {}):
    data = {"query" : query, "variables" : vars}
    data = json.dumps(data)
    data = data.encode()
    r = urlopen(req, data=data)
    content = json.loads(r.read().decode("utf-8"))
    content["status"]= r.getcode()
    errored, message = check_content(content, step)
    return content, errored, message

def check_content(content, step):
    if content["status"]!=200:
        return True, error_hitting_warhorn(content["status"], step)
    elif "errors" in content.keys():
        return True, error_from_warhorn(content, step)
    else:
        return False, "no errors"

def error_hitting_warhorn(status, step):
    return f"Error: {step} request failed to reach warhorn with status {status}"

def error_from_warhorn(content, step):
    errors = content["errors"]
    error_string = "; ".join([f"{x['message']} at {x['locations']}" for x in errors])
    return f"Error: {step} failed on warhorn with message: {error_string}"

def get_event_id(req,event_str, warhorn_queries):
    content, errored, message = submit_warhorn(req,"event_query",warhorn_queries["event_query"],vars ={"slug":event_str})
    return content["data"]["event"]["id"]

def get_gm_role_id(req, event_str, warhorn_queries):
    content, errored, message = submit_warhorn(req, "event_roles", warhorn_queries["event_roles"], vars = {"slug":event_str})
    for d in content["data"]["event"]["roles"]:
        if d["name"]=="GM":
            return d["id"]

def get_gamesystem_id(req, entry, warhorn_queries):
    step = "gamesystems_query"
    content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars =entry)
    if errored:
        return errored, message
    else:
        games = content["data"]["gameSystems"]["nodes"]
        if len(games)>0:
            entry["gameSystemId"]=games[0]["id"]
            return False, entry
        else:
            content, errored, message = submit_warhorn(req, "gamesystems_mutation", warhorn_queries["gamesystems_mutation"], vars =entry)
            if errored:
                return errored, message
            else:
                entry["gameSystemId"]=content["data"]["createGameSystem"]["gameSystem"]["id"]
                return False, entry

def create_slot_get_id(req, entry, warhorn_queries):
    step = "get_current_slots"
    content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
    if errored:
        return errored, message
    else:
        current_slots = content["data"]["event"]["slots"]["nodes"]
        for slot in current_slots:
            if slot["startsAt"] == entry["startsAt"] and slot["endsAt"] == entry["endsAt"]:
                entry["slotId"] = slot["id"]
                return False, entry
        step = "create_slot"
        content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
        if errored:
            return errored, message
        else:
            entry["slotId"]=content["data"]["createSlot"]["slot"]["id"]
            return False, entry

def create_scenario_get_id(req, entry, warhorn_queries):
    step = "event_scenarios"
    content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
    if errored:
        return errored, message
    else:
        scenarios = content["data"]["eventScenarioOfferings"]["nodes"]
        for sce in scenarios:
            if sce["scenario"]["name"] == entry["name"]:
                entry["scenarioId"] = sce["scenario"]["id"]
                return False, entry

        step = "create_scenario"
        content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
        if errored:
            return errored, message
        else:
            entry["scenarioId"] = content["data"]["createEventScenario"]["scenario"]["id"]
            return False, entry

def create_event_session(req, entry, warhorn_queries):
    step = "query_sessions"
    content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
    if errored:
        return errored, message
    else:
        sessions = content["data"]["eventSessions"]["nodes"]
        for s in sessions:
            if s["name"]==entry["name"] and s["scenario"]["id"]==entry["scenarioId"] and s["slot"]["id"]==entry["slotId"]:
                entry["sessionId"]= s["id"]
                return False, entry
        step = "create_session"
        content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
        if errored:
            return errored, message
        else:
            entry["sessionId"] = content["data"]["createEventSession"]["session"]["id"]
            return False, entry
            
def assign_gm_role(req, entry, warhorn_queries):
    step = "get_registration_query"
    content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
    if errored:
        return errored, message
    else:
        if content["data"]["eventRegistration"] is None:
            return True, "Attendee has not registered for event"
        else:
            entry["registrationId"] = content["data"]["eventRegistration"]["id"]
            entry["userId"] = content["data"]["eventRegistration"]["registrant"]["id"]
            
            step = "check_session_gm"
            content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
            if errored:
                return errored, message
            else:
                sessions = content["data"]["eventSessions"]["nodes"]
                for s in sessions:
                    if s["id"]==entry["sessionId"]:
                        available_gm_seats = s["availableGmSeats"]

            if available_gm_seats > 0:
                step = "claim_gm_slot"
                content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
                if errored:
                    return errored, message
                else:
                    signup = content["data"]["claimGmSignup"]
                    if "signup" in signup.keys():
                        return False, entry
                    else:
                        return True, "Failed to claim GM slot"
                    
            else:
                return False, entry

def publish_game(req, entry, warhorn_queries):
    step = "check_session_status"
    content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)

    if errored:
        return errored, message
    else:
        sessions = content["data"]["eventSessions"]["nodes"]
        for s in sessions:
            if s["id"]==entry["sessionId"]:
                status = s["status"]

        if status == "DRAFT":
            step ="publish_game"
            content, errored, message = submit_warhorn(req, step, warhorn_queries[step], vars = entry)
            if errored:
                return errored, message
            else:
                if content["data"]["publishEventSession"]["session"]["id"] == entry["sessionId"]:
                    entry["completed"] = True
                    return False, entry
                else:
                    return True, "Failed to publish session"
        else:
            return False, entry



def fix_date(string):
    l =string.split(", ")
    date = datetime.strptime(l[1] + " " + l[2], "%B %d %Y")
    return date.strftime("%Y-%m-%d")

def fix_start_time(string):
    time = datetime.strptime(string, "%I:%M:%S %p")
    return time.strftime("%H:%M:%S")

def create_start_datetime(x):
    raw_date_time = x.date + "T" + x.start_time

    date_time = datetime.strptime(raw_date_time, "%Y-%m-%dT%H:%M:%S")

    #manually adjusting time to 
    date_time = date_time - timedelta(hours = 3)
    return date_time.strftime("%Y-%m-%dT%H:%M:%S")

def create_end_datetime(x):
    
    start_date_time =datetime.strptime(x.start_date_time, "%Y-%m-%dT%H:%M:%S")

    end_date_time = start_date_time + timedelta(hours = int(x.duration))

    return end_date_time.strftime("%Y-%m-%dT%H:%M:%S")


def main(token, sheet_id, event_str, warhorn_queries, col_rename):
    
    df = get_submissions(sheet_id)
    df["slug"]= event_str

    # Updating column names to match queries and mutations submitted
    df.rename(columns=col_rename, inplace=True)

    # Dropping extra columns from google sheet
    df.dropna(axis = 1, how ="all", inplace=True) 
    
    
    # Dropping any rows missing required values except for art column
    clean_df = df.dropna(axis=0, subset=[x for x in col_rename.values() if x not in ["art", "gm_name"]], how="any")
    dropped_df = df[~df.index.isin(clean_df.index)]
    dropped_records = dropped_df[["Timestamp"] + list(col_rename.values())].to_dict("records")
    
    df = clean_df

    df.fillna(value="", inplace=True)
    # Fixing date format
    df["date"]=df["date"].apply(fix_date)
    df["start_time"]=df["start_time"].apply(fix_start_time)
    df["start_date_time"]=df.apply(create_start_datetime, axis =1)
    df["end_date_time"]=df.apply(create_end_datetime, axis =1)

    #manually adding timezone for graphql submission 
    df["startsAt"]=df["start_date_time"] + "-08:00"
    df["endsAt"]=df["end_date_time"] + "-08:00"

    df["timezone"] = "America/New_York"

    req = Request("https://warhorn.net/graphql", method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header("Authorization", "bearer " + token)
    
    clean_df["eventId"] = get_event_id(req, event_str, warhorn_queries)
    clean_df["roleId"] = get_gm_role_id(req, event_str, warhorn_queries)
    clean_df["tableCount"] = 1
    clean_df["tableSize"]=clean_df["tableSize"].astype('int')

    clean_df["notes"] = clean_df["notes"] + "\n\n" + clean_df["blurb"]

    entries = clean_df.to_dict("records")

    func_list = [get_gamesystem_id, create_scenario_get_id, create_slot_get_id,create_event_session, assign_gm_role, publish_game]

    error_list =[]

    completed_entries =[]
    for e in entries:
        print(f"starting entry {entries.index(e)} "+20*"*")
        errored = False
        func_i = 0
        timestamp = e["Timestamp"]
        name = e["name"]
        gm = e["gm_name"]
        email = e["email"]
        while func_i < len(func_list):
            func = func_list[func_i]
            errored, e = func(req, e, warhorn_queries)
            func_i += 1
            if errored:
                error_list.append((timestamp, name, gm, email, e))
                break
        if type(e) is dict:
            completed_entries.append((timestamp,name,e["start_date_time"],gm,email))

    return completed_entries, error_list, dropped_records

        

if __name__ == "__main__":
    print("testing")
    
    with open("col_rename.json") as file:
        col_rename = json.load(file)

    with open("warhorn_creds.json") as file: # Use file to refer to the file object
        creds = json.load(file)
    
    with open("warhorn_queries.json") as file:
        warhorn_queries =json.load(file)

    
    completed_entries, error_list, dropped_df = main(creds["user_access_token"], 
                                  creds["sheet_id"],
                                    creds["event_str"],
                                warhorn_queries,
                                col_rename)
    
    print(completed_entries)
    print(error_list)
    print(dropped_df)
    
    # req = Request("https://warhorn.net/graphql", method="POST")
    # req.add_header('Content-Type', 'application/json')
    # req.add_header("Authorization", "bearer " + creds["user_access_token"])
    # print(submit_warhorn(req))

    # entry = {'Timestamp': '1/6/2023 14:43:40', 'email': 'bryanjonker@gmail.com', "GM's Discord Identity": 'bryanjonker#7049', 'This event will be, in part, run on the Games on Demand Discord. Do you need an invite?': "No, I'm already there.", 'name': 'Companionless', 'system': 'Firefly, 1st Edition', 'blurb': "In the city of New Vega on Paquin, a naïve companion is missing, and it is up to a team, some Companions, some friends of the victim, all hired by the Companion Guild to find what really happened. If she is alive, bring her back. If she is dead, get justice. The Companions aren't some Jien Huo that can be thrown away. The Guild protects their own.", 'tablesize': 8.0, 'notes': 'Zoom', 'date': '2023-02-25', 'start_time': '09:00:00', 'duration': 4.0, 'art': "", 'Would you like to help run Games on Demand Online now or in the future?': "", 'Anything else you recommend the organizers of Games on Demand should take into account?': 'New players welcome, characters will be provided', 'GM Name (for event promotion)': 'Bryan Jonker', 'Minimum Number of Players': 5.0, 'slug': 'drew_testing_event', 'start_date_time': '2023-02-25T06:00:00', 'end_date_time': '2023-02-25T10:00:00', 'startsAt': '2023-02-25T06:00:00-08:00', 'endsAt': '2023-02-25T10:00:00-08:00', 'timezone': 'America/New_York', 'eventId': 'RXZlbnQtODUyNw==', 'roleId': 'RXZlbnRSb2xlLTIzOTEz'}
    # step = "gamesystems_query"
    # print(submit_warhorn(req, step, warhorn_queries[step], vars =entry))
    # print(get_gamesystem_id(req, {'system': 'Firefly, 1st Edition'}))
    
    # print(submit_warhorn(req, 
    #                      query = warhorn_queries["get_registration_query"], 
    #                      vars ={"email":"drder@gmail.com","slug": "games-on-demand-online-2023"}
    #                      ))
    
    # print(submit_warhorn(req, 
    #                      query = warhorn_queries["get_registration_query"], 
    #                      vars ={"email":"drduber@gmail.com","slug": "games-on-demand-online-2023"}
    #                      ))