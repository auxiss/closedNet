import json
import os
import sys
import rsa_enryption as rsa


def create_config_file(token: str, username: str, group_name: str, group_key: str):

    key_pair = rsa.generate_rsa_keys()

    file_name = f"{username}_{group_name}.json"


    config = {
        "token": token,
        "PEM_private_key": key_pair[0].decode(),
        "PEM_public_key": key_pair[1].decode(),
        "username": username,
        "group_name": group_name,
        "group_key": group_key,
        "members": []
    }

    #check if it already exists
    if os.path.exists(file_name):
        print("Config file already exists. Do you want to overwrite it? (y/n)")
        choice = input().lower()
        if choice != 'y':
            print("Aborting config file creation.")
            return
        
    with open(file_name, "w") as f:
        json.dump(config, f, indent=4)
    print("Config file created successfully.")



def load_config_file(file_name) -> dict:
    if not os.path.exists(file_name):
        print("Config file not found. Please create a config file first.")
        sys.exit(1)

    with open(file_name, "r") as f:
        config = json.load(f)
    
    return config

def add_member_to_config(file_name: str, name: str, rsa_public_key: str):
    member_data = {
        "name": name,
        "rsa_public_key": rsa_public_key
    }
    config = load_config_file(file_name)
    members = config.get("members", [])
    members.append(member_data)
    config["members"] = members

    with open(file_name, "w") as f:
        json.dump(config, f, indent=4)
    print("Member added to config file successfully.")

def get_members_from_config(file_name: str) -> list[dict]:
    config = load_config_file(file_name)
    return config.get("members", [])



if __name__ == "__main__":
    # Example usage:
    token = input("Enter your GitHub token: ")
    username = input("Enter your username: ")
    group_name = input("Enter the group name: ")
    group_key = input("Enter the group key (must be a string): ")

    file_name = f"{username}_{group_name}.json"

    create_config_file(token, username, group_name, group_key)
    config = load_config_file(file_name)
    print(config)

