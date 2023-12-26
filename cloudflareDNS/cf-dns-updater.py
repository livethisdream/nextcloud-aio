import requests
import json
import logging
import configparser

config = configparser.ConfigParser()
config.read('/Users/rogers/nextcloud-aio/cloudflareDNS/dnsConfig.ini') # location of the config file


# Cloudflare API credentials
email = config['CF']['email']
api_key = config['CF']['apikey']
zone_id = config['CF']['zoneid']
standalone = config['OTHER'].getboolean('standalone')
cf_domain = config['CF']['domain']
constant_log = config['OTHER'].getboolean('constantLog')
logLoc = config['OTHER']['logFileLoc']

# Set up logging
logging.basicConfig(filename=logLoc, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cloudflare API endpoint for updating DNS records
cf_base_api_url: str = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/'


# function to get current record info
def get_record_info():
    api_url: str = cf_base_api_url + f'dns_records?type=A&name={cf_domain}'
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key,
        # "Authorization": api_key
    }
    response = requests.get(api_url, headers=headers)
    # get status, record id, and current ip
    resp_status: int = response.status_code
    if resp_status != 200:
        dns_ip = ''
        dns_record_id = ''
    else:
        r = response.json()
        dns_ip: str = r['result'][0]['content']
        dns_record_id: str = r['result'][0]['id']
    return resp_status, dns_ip, dns_record_id


# Function to get public IP address
def get_public_ip():
    response = requests.get("https://api64.ipify.org?format=json")
    ip_data = json.loads(response.text)
    return ip_data["ip"]


# Function to update Cloudflare DNS A record

def update_dns_record(ip_address):
    api_url = cf_base_api_url + f'dns_records/{record_id}'
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Email": email,
        "X-Auth-Key": api_key,
    }

    data = {
        "type": "A",
        "name": cf_domain,  # Replace with your domain name
        "content": ip_address,
    }

    response = requests.put(api_url, headers=headers, data=json.dumps(data))
    return response.json()


# Main script
if __name__ == "__main__":

    try:
        public_ip = get_public_ip()
        status, current_ip, record_id = get_record_info()
        if status == 200:
            if public_ip != current_ip:
                update_result = update_dns_record(public_ip)
                if update_result["success"]:
                    logging.info(f"DNS A record updated successfully. New IP: {public_ip}")
                    print(f"DNS A record updated successfully. New IP: {public_ip}")
                else:
                    error_message = f"Failed to update DNS A record. Error: {update_result['errors'][0]['message']}"
                    logging.error(error_message)
                    if standalone:
                        print(error_message)
            else:
                if constant_log:
                    info_msg: str = 'DNS IP matches Public IP, IP address not updated.'
                    logging.info(info_msg)
                    if standalone:
                        print(info_msg)
        else:
            error_message = f"API called returned status: {str(status)}. IP address not updated."
            logging.error(error_message)
            if standalone:
                print(error_message)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        logging.error(error_message)
        if standalone:
            print(error_message)
