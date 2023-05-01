from bech32m_chia import bech32m
from wallet import Wallet
import requests
from time import sleep
from typing import List, Dict

collection_ids = [
    "col18tmrzuymm86qefvuq28qh8d92daw4yqupzpjryvnlhg88rlp24tqtr3ja8",
    "col1s626wpqgr0p8ktvgxatz8vp669adrxamqwzqe2rvd7tns2jtg8aqlyewa9"]
wallet_id = 5


def fetch_collection(collection_id: str, require_owners: bool) -> dict:
    """
    Fetch data from the API and return it as a dictionary.
    """
    data = {"items": []}
    params = {
        "require_owner": str(require_owners).lower(),
        "require_price": "false",
        "size": "100"}

    while True:
        try:
            response = requests.get(
                f"https://api.mintgarden.io/collections/{collection_id}/nfts",
                params=params)
            # Raise an HTTPError if the status code is >= 400.
            response.raise_for_status()
            page_data = response.json()
            if not page_data["items"]:  # Check if the page has no items
                break
            data["items"].extend(page_data["items"])
            if "next" not in page_data:
                break
            params["page"] = page_data["next"]
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while making a request to the API: {e}")
            break
    return data


def fetch_nft_data(encoded_id: str) -> dict:
    """
    Fetch NFT data from the API and return it as a dictionary.
    """
    try:
        response = requests.get(
            f"https://api.mintgarden.io/nfts/{encoded_id}")
        # Raise an HTTPError if the status code is >= 400.
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making a request to the API: {e}")
        data = {}
    return data


def nft_ownership_data(collection_ids: List[str]) -> List[Dict[str, any]]:
    nft_ownership_data: Dict[str, Dict[str, any]] = {}
    for collection_id in collection_ids:
        data = fetch_collection(collection_id, False)
        nft_values = [fetch_nft_data(item['encoded_id'])[
            'data']['metadata_json']['attributes'][5]['value'] for item in data['items']]
        for item, nft_value in zip(data['items'], nft_values):
            encoded_id = item['encoded_id']
            owner_address_encoded_id = item['owner_address_encoded_id']
            decoded_address = bech32m.decode_puzzle_hash(
                owner_address_encoded_id)
            nft_ownership_data.setdefault(decoded_address, {'owner_address_decoded_id': decoded_address,
                                                            'encoded_ids': [],
                                                            'nft_values': [],
                                                            'nft_value': 0})
            nft_ownership_data[decoded_address]['encoded_ids'].append(
                encoded_id)
            nft_ownership_data[decoded_address]['nft_values'].append(nft_value)
            nft_ownership_data[decoded_address]['nft_value'] += nft_value

    return list(nft_ownership_data.values())


def send_transactions(
        wallet_id: int, addition_list: List[Dict], coins=None, coin_announcements=None, puzzle_announcements=None) -> None:
    num_additions = len(addition_list)
    num_batches = (num_additions + 14) // 15
    for i in range(num_batches):
        batch = addition_list[i * 15:(i + 1) * 15]
        if batch:
            transaction = wallet.send_transaction_multi(
                wallet_id=wallet_id, additions=batch, fee=5000000, coins=coins, coin_announcements=coin_announcements, puzzle_announcements=puzzle_announcements)
            print(transaction)
            sleep(180)


if __name__ == "__main__":
    wallet = Wallet()
    addition_list = []

    nft_ownership_data = nft_ownership_data(collection_ids)

    for line in nft_ownership_data:
        owner_address_decoded_id = line['owner_address_decoded_id']
        nft_value = line['nft_value'] * 1
        addition_list.append({"amount": nft_value,
                              "puzzle_hash": f"0x{owner_address_decoded_id}",
                              "memos": []})
    sent = send_transactions(wallet_id, addition_list)
