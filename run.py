__version__ = '0.1'
__author__ = 'Oren Brigg'
__author_email__ = 'obrigg@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"


import meraki
from rich import print as pp
from rich.console import Console
from rich.table import Table
from openpyxl import Workbook


def select_org() -> str:
    # Fetch and select the organization
    print('\n\nFetching organizations...\n')
    organizations = dashboard.organizations.getOrganizations()
    ids = []
    table = Table(title="Meraki Organizations")
    table.add_column("Organization #", justify="left", style="cyan", no_wrap=True)
    table.add_column("Org Name", justify="left", style="cyan", no_wrap=True)
    counter = 0
    for organization in organizations:
        ids.append(organization['id'])
        table.add_row(str(counter), organization['name'])
        counter+=1
    console = Console()
    console.print(table)
    isOrgDone = False
    while isOrgDone == False:
        selected = input('\nKindly select the organization ID you would like to query: ')
        try:
            if int(selected) in range(0,counter):
                isOrgDone = True
            else:
                print('\t[bold red]Invalid Organization Number\n')
        except:
            print('\t[bold red]Invalid Organization Number\n')
    return(organizations[int(selected)]['id'])


def check_wifi_channel_utilization(network_id: str) -> dict:
    """
    This fuction checks the wifi channel utilization for a given network. 
    if the channel utilization is above the threshold, the check will fail.

    it will return a dictionary with the result for each AP.
    e.g. {
    'is_ok': False,
    'Q2KD-XXXX-XXXX': {'is_ok': False, 'utilization': 51.66},
    'Q2KD-XXXX-XXXX': {'is_ok': False, 'utilization': 56.69},
    'Q2KD-XXXX-XXXX': {'is_ok': True, 'utilization': 16.93},
    'Q2KD-XXXX-XXXX': {'is_ok': False, 'utilization': 59.48}
    }
    """
    result = {'is_ok': True}
    channel_utilization = dashboard.networks.getNetworkNetworkHealthChannelUtilization(network_id, perPage=100)
    # TODO: pagination
    for ap in channel_utilization:
        max_util = 0
        for util in ap['wifi1']:
            if util['utilization'] > max_util:
                max_util = util['utilization']
        if max_util > thresholds['5G Channel Utilization']:
            pp(f"[bold red]5G Channel Utilization reached {max_util}% - above {thresholds['5G Channel Utilization']}% for AP {ap['serial']}")
            result[ap['serial']] = {'is_ok': False, 'utilization': max_util}
            result['is_ok'] = False
        elif max_util == 0:
            print(f"AP {ap['serial']} does not have 5GHz enabled. Skipping...")
        else:
            pp(f"[green]5G Channel Utilization reached {max_util}% - below {thresholds['5G Channel Utilization']}% for AP {ap['serial']}")
            result[ap['serial']] = {'is_ok': True, 'utilization': max_util}
    return result


def check_wifi_rf_profiles(network_id: str) -> dict:
    """
    This fuction checks the RF profiles for a given network. 

    it will return a dictionary with the result for each AP.
    e.g. {
    'is_ok': False,
    'RF Profile 1': {'is_ok': False, 'min_power': 30, 'min_bitrate': 12, 'channel_width': '80', 'rxsop': None},
    'RF Profile 2': {'is_ok': True, 'min_power': 2, 'min_bitrate': 12, 'channel_width': 'auto', 'rxsop': None}
    }

    """
    result = {'is_ok': True}
    rf_profiles = dashboard.wireless.getNetworkWirelessRfProfiles(network_id)
    for rf_profile in rf_profiles:
        result[rf_profile['name']] = {  'is_ok': True, 
                                        'tests': {
                                            'min_power': {'is_ok': True},
                                            'min_bitrate': {'is_ok': True},
                                            'channel_width': {'is_ok': True},
                                            'rxsop': {'is_ok': True}
                                        }}
        # Check min TX power
        if rf_profile['fiveGhzSettings']['minPower'] > thresholds['5G Min TX Power']:
            pp(f"[bold red]The min TX power is too high at {rf_profile['fiveGhzSettings']['minPower']}dBm (not including antenna gain) for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['min_power'] = {'is_ok': False, 'value': rf_profile['fiveGhzSettings']['minPower']}
            result[rf_profile['name']]['is_ok'] = False
            result['is_ok'] = False
        else:
            pp(f"[green]The min TX power is {rf_profile['fiveGhzSettings']['minPower']}dBm for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['min_power'] = {'is_ok': True, 'value': rf_profile['fiveGhzSettings']['minPower']}
        
        # Check min bitrate
        if rf_profile['fiveGhzSettings']['minBitrate'] < thresholds['5G Min Bitrate']:
            pp(f"[bold red]The min bitrate is {rf_profile['fiveGhzSettings']['minBitrate']}Mbps for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['min_bitrate'] = {'is_ok': False, 'value': rf_profile['fiveGhzSettings']['minBitrate']}
            result[rf_profile['name']]['is_ok'] = False
            result['is_ok'] = False
        else:
            pp(f"[green]The min bitrate is {rf_profile['fiveGhzSettings']['minBitrate']}Mbps for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['min_bitrate'] = {'is_ok': True, 'value': rf_profile['fiveGhzSettings']['minBitrate']}
        
        # Check channel width
        if rf_profile['fiveGhzSettings']['channelWidth'] == "auto":
            pp(f"[bold red]The channel width is {rf_profile['fiveGhzSettings']['channelWidth']} for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['channel_width'] = {'is_ok': False, 'value': rf_profile['fiveGhzSettings']['channelWidth']}
            result[rf_profile['name']]['is_ok'] = False
            result['is_ok'] = False
        elif int(rf_profile['fiveGhzSettings']['channelWidth']) > thresholds['5G Max Channel Width']:
            pp(f"[bold red]The channel width is {rf_profile['fiveGhzSettings']['channelWidth']}MHz for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['channel_width'] = {'is_ok': False, 'value': rf_profile['fiveGhzSettings']['channelWidth']}
            result[rf_profile['name']]['is_ok'] = False
            result['is_ok'] = False
        else:
            pp(f"[green]The channel width is {rf_profile['fiveGhzSettings']['channelWidth']}MHz for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['channel_width'] = {'is_ok': True, 'value': rf_profile['fiveGhzSettings']['channelWidth']}
        
        # Check if rx-sop is confiugred
        if rf_profile['fiveGhzSettings']['rxsop'] != None:
            pp(f"[red]RX-SOP is configured for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['rxsop'] = {'is_ok': False, 'value': rf_profile['fiveGhzSettings']['rxsop']}
            result[rf_profile['name']]['is_ok'] = False
            result['is_ok'] = False
        else:
            pp(f"[green]RX-SOP is not configured for RF profile {rf_profile['name']}")
            result[rf_profile['name']]['rxsop'] = {'is_ok': True, 'value': rf_profile['fiveGhzSettings']['rxsop']}
    return (result)

if __name__ == '__main__':
    # Thresholds
    thresholds = {
        '5G Channel Utilization': 20,
        '5G Min TX Power': 10,
        '5G Min Bitrate': 12,
        '5G Max Channel Width': 40
    }

    # Initializing Meraki SDK
    dashboard = meraki.DashboardAPI()
    org_id = select_org()
    results = {}
    
    # Get networks
    networks = dashboard.organizations.getOrganizationNetworks(org_id)
    for network in networks:
        network_id = network['id']
        results[network['name']] = {}
        if "wireless" in network['productTypes']:
                # Wireless checks
                pp(3*"\n", 100*"*", 3*"\n")
                results[network['name']]['channel_utilization_check'] = check_wifi_channel_utilization(network_id)
                pp(3*"\n", 100*"*", 3*"\n")
                results[network['name']]['rf_profiles_check'] = check_wifi_rf_profiles(network_id)
                pp(3*"\n", 100*"*", 3*"\n")
                # TODO: wireless health
        
        if "switch" in network['productTypes']:
            # Wired checks

            # TODO: check for CRC errors
            # TODO: check for high broadcasts/multicasts rates, especially towards APs
            # TODO: check for large broadcast domains / number of clients on a Vlan
            pass

    pp(3*"\n", 100*"*", 3*"\n")
    
    # Results cleanup
    for result in results:
        if results[result] == {}:
            del results[result]

    # TODO: generate a report out of the results
    pp(results)
