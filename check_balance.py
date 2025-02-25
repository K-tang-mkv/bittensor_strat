import os
import asyncio
import argparse
import time

from bittensor_cli.src.bittensor.subtensor_interface import SubtensorInterface
from bittensor_cli.src import COLOR_PALETTE
from bittensor_cli.src.bittensor.utils import (
    console
)

from utils import wallet_ask, _calculate_slippage

async def main(subtensor, wallet):
    async with subtensor:
        initiated = True
    if initiated:
        with console.status(
                f"Retrieving subnet data & identities from {subtensor.network}...",
                spinner="earth",
        ):
            all_sn_dynamic_info_ = await subtensor.all_subnets()

            all_sn_dynamic_info = {info.netuid: info for info in all_sn_dynamic_info_}

        with console.status(
                f"Retrieving stake data from {subtensor.network}...",
                spinner="earth",
        ):
            # cold_hot = await sub.fetch_coldkey_hotkey_identities()
            stake_infos = await subtensor.get_stake_for_coldkey(
            coldkey_ss58=wallet.coldkeypub.ss58_address
            )
            stake_in_netuids = {}
            total_stake = 0
            for stake_info in stake_infos:
                if stake_info.hotkey_ss58 not in stake_in_netuids:
                    stake_in_netuids[stake_info.hotkey_ss58] = {}
                stake_in_netuids[stake_info.hotkey_ss58][stake_info.netuid] = (
                    stake_info.stake
                )

                received_amount, _, _ = _calculate_slippage(
                subnet_info=all_sn_dynamic_info[stake_info.netuid], amount=stake_info.stake)

                total_stake += received_amount
            
        with console.status(
                f"Retrieving current free balance from {subtensor.network}...",
                spinner="earth",
        ):
            balance = await subtensor.get_balance(wallet.coldkeypub.ss58_address)
        console.print("Total_stake: ", total_stake, '\n', "Free Balance: ", balance, '\n', "Total TAO: ", total_stake+balance)
        
def parse_args():
    parser = argparse.ArgumentParser(description="Register a neuron in a subnet.")
    parser.add_argument(
        '--wallet_name', 
        type=str, 
        required=True, 
        help='Coldkey wallet name'
    )
    parser.add_argument(
        '--wallet_path', 
        type=str, 
        default='~/.bittensor/wallets', 
        help='Path to wallet (default: ~/.bittensor/wallets)'
    )
    parser.add_argument(
        '--hotkey', 
        type=str, 
        required=False, 
        help='Hotkey wallet name'
    )
    parser.add_argument(
        '--network', 
        type=str, 
        default='finney', 
        help='Network name (default: finney)'
    )
    parser.add_argument(
         '--password',
         type=str,
         required=False,
         help="the coldkey's password!"
    )
    return parser.parse_args()
if __name__ == "__main__":
    subtensor = SubtensorInterface("wss://entrypoint-finney.opentensor.ai:443")
    args = parse_args()
    
    wallet = wallet_ask(args.wallet_name, args.wallet_path)
    asyncio.run(main(subtensor, wallet))