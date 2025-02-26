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
from utils import _safe_unstake_extrinsic

async def unstake_(sub, wallet, netuid, mini_sell):
    async with sub:
        initiated = True
    if initiated:
        while True:
            """Unstake from hotkey(s)."""

            with console.status(
                f"Retrieving stake data from {subtensor.network}...",
                spinner="earth",
            ):
                # Fetch stake balances
                chain_head = await subtensor.substrate.get_chain_head()
                stake_info_list = await subtensor.get_stake_for_coldkey(
                    coldkey_ss58=wallet.coldkeypub.ss58_address,
                    block_hash=chain_head,
                )
                stake_in_netuids = []
                for stake_info in stake_info_list:
                    if stake_info.netuid == netuid:
                        stake_in_netuids.append((stake_info.hotkey_ss58, stake_info.stake))
            
            if len(stake_in_netuids) == 0:
                console.print(
                    f"No any stake in this subnet {netuid}, wait for one hour and check again..."
                )
                time.sleep(3600) # if there was no alpha stake on this hotkey, wait one hour and check again

                continue

            for item in stake_in_netuids:
                with console.status(
                f"Retrieving subnet data & identities from {subtensor.network}...",
                spinner="earth",
                ):
                    all_sn_dynamic_info_ = await subtensor.all_subnets()

                    all_sn_dynamic_info = {info.netuid: info for info in all_sn_dynamic_info_}
                if item[1] is None:
                    console.print(
                        f"current hotkey {item[0]} stake alpha in this subnet {netuid} is None, check the next one"
                    )
                    continue
                else:
                    staking_address_ss58 = item[0]
                    current_stake_balance = item[1]
                    subnet_info = all_sn_dynamic_info.get(netuid)

                    # Determine the amount we are unstaking.
                    amount_to_unstake_as_balance = current_stake_balance

                    # Check enough stake to remove.
                    amount_to_unstake_as_balance.set_unit(netuid)

                    received_amount, _, slippage_pct_float = _calculate_slippage(
                        subnet_info=subnet_info, amount=amount_to_unstake_as_balance
                    )

                    if received_amount.tao > mini_sell:
                        # Additional fields for safe unstaking
                        if subnet_info.is_dynamic:
                            price_with_tolerance = subnet_info.price.rao * (
                                1 - (slippage_pct_float/100 * 2.1)
                            )  # Actual price to pass to extrinsic
                        else:
                            price_with_tolerance = 1
                    
                        with console.status("\n:satellite: Performing unstaking operations...") as status:
                            await _safe_unstake_extrinsic(
                                wallet=wallet,
                                subtensor=subtensor,
                                netuid=netuid,
                                amount=amount_to_unstake_as_balance,
                                current_stake=current_stake_balance,
                                hotkey_ss58=staking_address_ss58,
                                price_limit=price_with_tolerance,
                                allow_partial_stake=True,
                                status=status,
                            )
                        console.print(
                            f"[{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]Current hotkey {staking_address_ss58} Unstaking operations completed. Check the next one..."
                        )
                    else:
                        console.print(
                            f"[{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]Current hotkey {staking_address_ss58} Not satisfy mini sell {mini_sell}, check the next one..."
                        )


            console.print(f"All the hotkeys in this subnet {netuid} unstaking finish, wait for 30 minutes and check again...")
            time.sleep(1800)


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
        '--netuid', 
        type=int, 
        required=True, 
        help='Subnet ID'
    )
    parser.add_argument(
         '--password',
         type=str,
         required=True,
         help="the coldkey's password!"
    )
    parser.add_argument(
        '--mini_sell',
        type=float,
        required=True,
        help="minimum amount TAO to sell"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    subtensor = SubtensorInterface("wss://entrypoint-finney.opentensor.ai:443")
    
    wallet = wallet_ask(args.wallet_name, args.wallet_path, args.hotkey)
    password = os.environ.get("WALLET_PASSWORD")
    password = args.password
    wallet.coldkey_file.save_password_to_env(password)

    wallet.unlock_coldkey()
    asyncio.run(unstake_(subtensor, wallet, args.netuid, args.mini_sell))
