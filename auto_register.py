import argparse
from bittensor_cli.src.commands.subnets import subnets
from bittensor_cli.src.bittensor.balances import Balance
from bittensor_cli.src.bittensor.subtensor_interface import SubtensorInterface

from typing import Optional
from utils import wallet_ask
import bittensor as bt
import asyncio
import os

from bittensor_cli.src.bittensor.extrinsics.registration import (
    register_extrinsic,
    burned_register_extrinsic,
)

import logging
logging.basicConfig(
    level=logging.INFO,               # 设置日志级别为 INFO，这样 INFO 级别以上的日志会被记录
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

async def subnets_register(
        wallet_name: str,
        wallet_path: str,
        wallet_hotkey: str,
        network: Optional[list[str]],
        netuid: int,
        max_cost: float,
        password: str
    ):
        """
        Register a neuron (a subnet validator or a subnet miner) in the specified subnet by recycling some TAO.

        Before registering, the command checks if the specified subnet exists and whether the user's balance is sufficient to cover the registration cost.

        The registration cost is determined by the current recycle amount for the specified subnet. If the balance is insufficient or the subnet does not exist, the command will exit with an error message.

        EXAMPLE

        [green]$[/green] btcli subnets register --netuid 1
        """
        wallet = wallet_ask(
            wallet_name,
            wallet_path,
            wallet_hotkey
        )
        wallet.coldkey_file.save_password_to_env(password)
        wallet.unlock_coldkey()
        subtensor = bt.subtensor(network="finney")
        
        while True:
           
            current_recycle_ = subtensor.get_hyperparameter(param_name="Burn", netuid=netuid)
            balance = subtensor.get_balance(wallet.coldkeypub.ss58_address)
            current_recycle = (
                Balance.from_rao(int(current_recycle_)) if current_recycle_ else Balance(0)
            )

            logging.info(f"current registration fee: = {current_recycle}")

            # Check balance is sufficient
            if balance < current_recycle:
                logging.error(
                    f"Insufficient balance {balance} to register neuron. Current recycle is {current_recycle} TAO"
                )
                return
            if max_cost < current_recycle.tao:
                logging.error(
                    f"Exceed the max_cost Current recycle is {current_recycle} TAO")
                return
            
            done = subtensor.burned_register(
                wallet=wallet,
                netuid=netuid
            )
            if done:
                logging.info("Landing Success!!!")
                return


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
         '--max_allowed_cost',
         type=float,
         default='0.1',
         help='maximum allowed register fee'
    )
    parser.add_argument(
         '--password',
         type=str,
         required=True,
         help="the coldkey's password!"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    # Initialize the command with parsed arguments
    asyncio.run(subnets_register(
        wallet_name=args.wallet_name,
        wallet_path=args.wallet_path,
        wallet_hotkey=args.hotkey,
        network=[args.network],
        netuid=args.netuid,
        max_cost=args.max_allowed_cost,
        password=args.password
    ))