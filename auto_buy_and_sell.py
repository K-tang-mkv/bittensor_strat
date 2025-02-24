import bittensor as bt
import time
import logging
import argparse
import os
import asyncio

from typing import TYPE_CHECKING, Optional
import typer

from bittensor_wallet import Wallet

from bittensor_cli.src.bittensor.balances import Balance
from bittensor_cli.src.bittensor.utils import (
    console,
    err_console,
    print_error,
)
from utils import wallet_ask

if TYPE_CHECKING:
    from bittensor_cli.src.bittensor.subtensor_interface import SubtensorInterface

logging.basicConfig(
    level=logging.INFO,               # 设置日志级别为 INFO，这样 INFO 级别以上的日志会被记录
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)


# Helpers
def _calculate_slippage(subnet_info, amount: Balance) -> tuple[Balance, str, float]:
    """Calculate slippage and received amount for unstaking operation.

    Args:
        dynamic_info: Subnet information containing price data
        amount: Amount being unstaked

    Returns:
        tuple containing:
        - received_amount: Balance after slippage
        - slippage_pct: Formatted string of slippage percentage
        - slippage_pct_float: Float value of slippage percentage
    """
    received_amount, slippage_pct_float = subnet_info.alpha_to_tao_with_slippage(
        amount
    )

    if subnet_info.is_dynamic:
        slippage_pct = slippage_pct_float
    else:
        slippage_pct_float = 0
        slippage_pct = "[red]N/A[/red]"

    return received_amount, slippage_pct, slippage_pct_float

async def _unstake_selection(
    wallet,
    netuid=None,
):
    subtensor = bt.async_subtensor("finney")
    await subtensor.initialize()
    
    # Test the connection works
    try:
        await subtensor.get_current_block()
    except Exception as e:
        await subtensor.close()
        raise e
    while True:
        all_sn_dynamic_info_ = await subtensor.all_subnets()
        dynamic_info = {info.netuid: info for info in all_sn_dynamic_info_}

        stake_infos_ = await subtensor.get_stake_for_coldkey(
            coldkey_ss58=wallet.coldkeypub.ss58_address
        )
        stake_infos = {(info.hotkey_ss58, info.netuid): info for info in stake_infos_}
        hotkey_ss58_address = wallet.hotkey.ss58_address
        if not stake_infos:
            print_error("You have no stakes to unstake.")
            raise typer.Exit()
        else:
            print(stake_infos[(hotkey_ss58_address, netuid)])

        stake = stake_infos[(hotkey_ss58_address, netuid)]
        received_amount, slippage_pct, slippage_pct_float = _calculate_slippage(dynamic_info[netuid], stake.stake)
        logging.info(f"received_amount: {received_amount} slippage_pct: {slippage_pct}")

        unstake_all_alpha = True
        console_status = (
            ":satellite: Unstaking all Alpha stakes..."
            if unstake_all_alpha
            else ":satellite: Unstaking all stakes..."
        )
        logging.info(f"received_rao: {received_amount.rao}")
        rao = received_amount.tao * pow(10, 9)
        logging.info(f"received_rao!!: {rao}")
        if received_amount.tao > 0.1:
            with console.status(console_status):
                
                # call_function = "unstake_all_alpha" if unstake_all_alpha else "unstake_all"
                # call = subtensor.substrate.compose_call(
                #     call_module="SubtensorModule",
                #     call_function="remove_stake",
                #     call_params={
                #         "hotkey": hotkey_ss58_address,
                #         "netuid": netuid,
                #         "amount_unstaked": received_amount.rao,
                #     },
                # )
                # success, error_message = subtensor.sign_and_send_extrinsic(
                #     cal Al=call,
                #     wallet=wallet,
                #     wait_for_inclusion=True,
                #     wait_for_finalization=False,
                # )
                success = await subtensor.unstake(wallet=wallet, hotkey_ss58=hotkey_ss58_address, netuid=netuid, wait_for_inclusion=True, wait_for_finalization=False)

                if success:
                    success_message = (
                        ":white_heavy_check_mark: [green]Successfully unstaked all stakes[/green]"
                        if not unstake_all_alpha
                        else ":white_heavy_check_mark: [green]Successfully unstaked all Alpha stakes [/green]"
                    )
                    console.print(success_message)
                    
                    return True
                else:
                    err_console.print(
                        f":cross_mark: [red]Failed to unstake[/red]:"
                    )
                    return False
        else:
            logging.info("can't swap")
            time.sleep(10)

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
    return parser.parse_args()

async def get_working_subtensor():
    """
    Get an initialized subtensor connection and test it works.
    Retries on failure, cycling through different endpoints.
    """
    sub = bt.async_subtensor("finney")
    await sub.initialize()
    
    # Test the connection works
    try:
        await sub.get_current_block()
        return sub
    except Exception as e:
        await sub.close()
        raise e

if __name__ == "__main__":
    logging.info("Start this app!!!")
    args = parse_args()

    wallet = wallet_ask(args.wallet_name, args.wallet_path, args.hotkey)
    password = args.password
    wallet.coldkey_file.save_password_to_env(password)
    
    wallet.unlock_coldkey()
    asyncio.run(_unstake_selection(wallet, args.netuid))

