import os
import asyncio
import argparse

from bittensor_cli.src.bittensor.subtensor_interface import SubtensorInterface
from async_substrate_interface.errors import SubstrateRequestException
from bittensor_cli.src import COLOR_PALETTE
from bittensor_cli.src.bittensor.utils import (
    console,
    print_error,
    format_error_message,
)

from utils import wallet_ask, _calculate_slippage

async def unstake(sub, wallet, netuid, mini_sell):
    async with sub:
        initiated = True
    if initiated:
        while True:
            all_sn_dynamic_info_ = await subtensor.all_subnets()
            all_sn_dynamic_info = {info.netuid: info for info in all_sn_dynamic_info_}   

            block_hash = await subtensor.substrate.get_chain_head()

            current_balance, next_nonce, current_stake = await asyncio.gather(
                subtensor.get_balance(wallet.coldkeypub.ss58_address, block_hash),
                subtensor.substrate.get_account_next_index(wallet.coldkeypub.ss58_address),
                subtensor.get_stake(
                    hotkey_ss58=wallet.hotkey.ss58_address,
                    coldkey_ss58=wallet.coldkeypub.ss58_address,
                    netuid=netuid,
                ),
            )

            subnet_info = all_sn_dynamic_info[netuid]
            received_amount, slippage_pct, slippage_pct_float = _calculate_slippage(subnet_info, current_stake)
            if received_amount.tao > mini_sell:
                amount_to_sell = current_stake
                rate_tolerance = slippage_pct_float / 100
                if subnet_info.is_dynamic:
                    price_with_tolerance = subnet_info.price.rao * (
                        1 - rate_tolerance
                    )  # Actual price to pass to extrinsic
                print(current_stake, received_amount, slippage_pct, current_stake*price_with_tolerance/pow(10, 9))
                print(current_balance, current_stake)

                failure_prelude = (
                    f":cross_mark: [red]Failed[/red] to unstake {received_amount} on Netuid {netuid}"
                )

                allow_partial_stake = True
                call = await subtensor.substrate.compose_call(
                    call_module="SubtensorModule",
                    call_function="remove_stake_limit",
                    call_params={
                        "hotkey": wallet.hotkey.ss58_address,
                        "netuid": netuid,
                        "amount_unstaked": amount_to_sell.rao,
                        "limit_price": price_with_tolerance,
                        "allow_partial": allow_partial_stake,
                    },
                )

                extrinsic = await subtensor.substrate.create_signed_extrinsic(
                    call=call, keypair=wallet.coldkey, nonce=next_nonce
                )

                try:
                    response = await subtensor.substrate.submit_extrinsic(
                        extrinsic, wait_for_inclusion=True, wait_for_finalization=False
                    )
                except SubstrateRequestException as e:
                    if "Custom error: 8" in str(e):
                        print_error(
                            f"\n{failure_prelude}: Price exceeded tolerance limit. "
                            f"Transaction rejected because partial unstaking is disabled. "
                            f"Either increase price tolerance or enable partial unstaking.",
                            status=None,
                        )
                        return
                    else:
                        print_error(
                            f"\n{failure_prelude} with error: {format_error_message(e)}"
                        )
                    return

                await response.process_events()
                if not await response.is_success:
                    print_error(
                        f"\n{failure_prelude} with error: {format_error_message(await response.error_message)}"
                    )
                    return

                block_hash = await subtensor.substrate.get_chain_head()
                new_balance, new_stake = await asyncio.gather(
                    subtensor.get_balance(wallet.coldkeypub.ss58_address, block_hash),
                    subtensor.get_stake(
                        hotkey_ss58=wallet.hotkey.ss58_address,
                        coldkey_ss58=wallet.coldkeypub.ss58_address,
                        netuid=netuid,
                        block_hash=block_hash,
                    ),
                )

                console.print(":white_heavy_check_mark: [green]Finalized[/green]")
                console.print(
                    f"Balance:\n  [blue]{current_balance}[/blue] :arrow_right: [{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]{new_balance}"
                )

                amount_unstaked = current_stake - new_stake
                if allow_partial_stake and (amount_unstaked != amount_to_sell):
                    console.print(
                        "Partial unstake transaction. Unstaked:\n"
                        f"  [{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]{amount_unstaked.set_unit(netuid=netuid)}[/{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}] "
                        f"instead of "
                        f"[blue]{amount_to_sell}[/blue]"
                    )

                console.print(
                    f"Subnet: [{COLOR_PALETTE['GENERAL']['SUBHEADING']}]{netuid}[/{COLOR_PALETTE['GENERAL']['SUBHEADING']}] "
                    f"Stake:\n  [blue]{current_stake}[/blue] :arrow_right: [{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]{new_stake}"
                )

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
        required=True, 
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
    asyncio.run(unstake(subtensor, wallet, args.netuid, args.mini_sell))
