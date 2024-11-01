from web3 import Web3
import time
import os
import random

# Connect to Taiko RPC
taiko_rpc_url = "https://rpc.ankr.com/taiko"
web3 = Web3(Web3.HTTPProvider(taiko_rpc_url))

# Check network connection
if not web3.is_connected():
    print("Tidak dapat terhubung ke jaringan Taiko.")
    exit()

# Replace with your actual private key and address
private_key = "isi peivate key"  # Ganti dengan private key
my_address = Web3.to_checksum_address("isi address")  # Alamat dompet Anda

weth_contract_address = Web3.to_checksum_address("0xA51894664A773981C6C112C43ce576f315d5b1B6")

# WETH contract ABI
weth_abi = '''
[
    {
        "constant":true,
        "inputs":[{"name":"account","type":"address"}],
        "name":"balanceOf",
        "outputs":[{"name":"balance","type":"uint256"}],
        "payable":false,
        "stateMutability":"view",
        "type":"function"
    },
    {
        "constant":false,
        "inputs":[{"name":"wad","type":"uint256"}],
        "name":"withdraw",
        "outputs":[],
        "payable":false,
        "stateMutability":"nonpayable",
        "type":"function"
    },
    {
        "constant":false,
        "inputs":[{"name":"wad","type":"uint256"}],
        "name":"deposit",
        "outputs":[],
        "payable":true,
        "stateMutability":"payable",
        "type":"function"
    }
]
'''

weth_contract = web3.eth.contract(address=weth_contract_address, abi=weth_abi)

amount_in_wei = web3.to_wei(0.026971, 'ether')  # Amount to swap
gas_price_gwei = 0.18  # Gas price in Gwei
max_priority_fee_per_gas = web3.to_wei(gas_price_gwei, 'gwei')
max_fee_per_gas = web3.to_wei(gas_price_gwei, 'gwei')


def check_eth_balance():
    balance = web3.eth.get_balance(my_address)
    eth_balance = web3.from_wei(balance, 'ether')
    print(f"Saldo ETH: {eth_balance:.6f} ETH")
    return balance


def check_weth_balance():
    balance = weth_contract.functions.balanceOf(my_address).call()
    weth_balance = web3.from_wei(balance, 'ether')
    print(f"Saldo WETH: {weth_balance:.6f} WETH")
    return balance


def get_next_nonce():
    return web3.eth.get_transaction_count(my_address)


def has_sufficient_balance(amount_in_wei, is_wrap=True):
    try:
        if is_wrap:
            gas_estimate = weth_contract.functions.deposit(amount_in_wei).estimate_gas({'from': my_address, 'value': amount_in_wei})
        else:
            gas_estimate = weth_contract.functions.withdraw(amount_in_wei).estimate_gas({'from': my_address})
        total_cost = max_priority_fee_per_gas * gas_estimate

        if is_wrap:
            eth_balance = check_eth_balance()
            if eth_balance >= total_cost:
                print(f"Sufficient ETH Balance. Required: {web3.from_wei(total_cost, 'ether')} ETH")
                return True
            else:
                print(f"Insufficient funds. Balance: {web3.from_wei(eth_balance, 'ether')} ETH, Required: {web3.from_wei(total_cost, 'ether')} ETH")
        else:
            weth_balance = check_weth_balance()
            if weth_balance >= amount_in_wei:
                print(f"Sufficient WETH Balance. Required: {web3.from_wei(amount_in_wei, 'ether')} WETH")
                return True
            else:
                print(f"Insufficient funds. Balance: {web3.from_wei(weth_balance, 'ether')} WETH, Required: {web3.from_wei(amount_in_wei, 'ether')} WETH")
        return False
    except Exception as e:
        print(f"Error estimating gas: {e}")
        return False


def wait_for_confirmation(tx_hash, timeout=300):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            receipt = web3.eth.get_transaction_receipt(tx_hash)
            if receipt:
                if receipt['status'] == 1:
                    print(f"Transaction Successful | Tx Hash: {web3.to_hex(tx_hash)} | Network: Taiko")
                    print(f"Transaction execution time: {int(time.time() - start_time)} seconds")
                    return True
                else:
                    print(f"Transaction Failed | Tx Hash: {web3.to_hex(tx_hash)}")
                    return False
        except Exception:
            pass
        time.sleep(30)  # Wait before checking again
    print(f"Timeout waiting for confirmation for Tx Hash: {web3.to_hex(tx_hash)}")
    return False


def wrap_eth_to_weth(amount_in_wei):
    if not has_sufficient_balance(amount_in_wei, is_wrap=True):
        print("Waiting for sufficient ETH balance...")
        return False

    nonce = get_next_nonce()
    gas_estimate = weth_contract.functions.deposit(amount_in_wei).estimate_gas({'from': my_address, 'value': amount_in_wei})
    transaction = {
        'to': weth_contract_address,
        'chainId': 167000,
        'gas': gas_estimate,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee_per_gas,
        'nonce': nonce,
        'value': amount_in_wei,
        'data': '0xd0e30db0'  # Deposit function signature
    }

    signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
    try:
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction sent: Wrapping ETH to WETH | Tx Hash: {web3.to_hex(tx_hash)} | Network: Taiko")
        if wait_for_confirmation(tx_hash):
            return True
    except Exception as e:
        print(f"Transaction error: {e}")
    return False


def unwrap_weth_to_eth(amount_in_wei):
    if not has_sufficient_balance(amount_in_wei, is_wrap=False):
        print("Waiting for sufficient WETH balance...")
        return False

    nonce = get_next_nonce()
    gas_estimate = weth_contract.functions.withdraw(amount_in_wei).estimate_gas({'from': my_address})
    transaction = {
        'to': weth_contract_address,
        'chainId': 167000,
        'gas': gas_estimate,
        'maxFeePerGas': max_fee_per_gas,
        'maxPriorityFeePerGas': max_priority_fee_per_gas,
        'nonce': nonce,
        'data': '0x2e1a7d4d' + amount_in_wei.to_bytes(32, 'big').hex()  # Withdraw function signature
    }

    signed_txn = web3.eth.account.sign_transaction(transaction, private_key)
    try:
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction sent: Unwrapping WETH to ETH | Tx Hash: {web3.to_hex(tx_hash)} | Network: Taiko")
        if wait_for_confirmation(tx_hash):
            return True
    except Exception as e:
        print(f"Transaction error: {e}")
    return False


wrap_counter = 0
unwrap_counter = 0
total_tx = 0

while total_tx < 74:
    eth_balance = check_weth_balance()

    # Wrap ETH to WETH
    if wrap_counter < 37 and total_tx < 74:
        if wrap_eth_to_weth(amount_in_wei):
            wrap_counter += 1
            total_tx += 1
            print(f"Total Transactions: {total_tx} (Wrapping: {wrap_counter})")

# Optional: Sleep for a random duration between transactions
    sleep_time = random.uniform(10, 20)
    print(f"Sleeping for {sleep_time:.2f} seconds before the next transaction.")
    time.sleep(sleep_time)

    weth_balance = check_eth_balance()

    # Unwrap WETH to ETH
    if unwrap_counter < 37 and total_tx < 74:
        if unwrap_weth_to_eth(amount_in_wei):
            unwrap_counter += 1
            total_tx += 1
            print(f"Total Transactions: {total_tx} (Unwrapping: {unwrap_counter})")

    # Optional: Sleep for a random duration between transactions
    sleep_time = random.uniform(10, 20)
    print(f"Sleeping for {sleep_time:.2f} seconds before the next transaction.")
    time.sleep(sleep_time)

print(f"Completed. Total Transactions: {total_tx} (Wrapping: {wrap_counter}, Unwrapping: {unwrap_counter})")
