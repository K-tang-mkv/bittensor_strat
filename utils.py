from typing import Optional
import os
from bittensor_wallet import Wallet
from bittensor_cli.src.bittensor.balances import Balance

import asyncio
from functools import partial

from bittensor_wallet import Wallet

from async_substrate_interface.errors import SubstrateRequestException
from bittensor_cli.src import COLOR_PALETTE
from bittensor_cli.src.bittensor.balances import Balance
from bittensor_cli.src.bittensor.utils import (
    console,
    print_error,
    format_error_message,
)

def wallet_ask(
        wallet_name: Optional[str],
        wallet_path: Optional[str],
        wallet_hotkey=None,
    ) -> Wallet:
        """
        Generates a wallet object based on supplied values, validating the wallet is valid if flag is set
        :param wallet_name: name of the wallet
        :param wallet_path: root path of the wallets
        :param wallet_hotkey: name of the wallet hotkey file
        :param validate: flag whether to check for the wallet's validity
        :param ask_type: aspect of the wallet (name, path, hotkey) to prompt the user for
        :return: created Wallet object
        """
        # Create the Wallet object
        if wallet_path:
            wallet_path = os.path.expanduser(wallet_path)
        wallet = Wallet(name=wallet_name, path=wallet_path, hotkey=wallet_hotkey)
        
        return wallet


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
    received_amount, _, slippage_pct_float = subnet_info.alpha_to_tao_with_slippage(
        amount
    )

    if subnet_info.is_dynamic:
        slippage_pct = f"{slippage_pct_float:.4f} %"
    else:
        slippage_pct_float = 0
        slippage_pct = "[red]N/A[/red]"

    return received_amount, slippage_pct, slippage_pct_float


async def _safe_unstake_extrinsic(
    wallet: Wallet,
    subtensor: "SubtensorInterface",
    netuid: int,
    amount: Balance,
    current_stake: Balance,
    hotkey_ss58: str,
    price_limit: Balance,
    allow_partial_stake: bool,
    status=None,
) -> None:
    """Execute a safe unstake extrinsic with price limit.

    Args:
        netuid: The subnet ID
        amount: Amount to unstake
        current_stake: Current stake balance
        hotkey_ss58: Hotkey SS58 address
        price_limit: Maximum acceptable price
        wallet: Wallet instance
        subtensor: Subtensor interface
        allow_partial_stake: Whether to allow partial unstaking
        status: Optional status for console updates
    """
    err_out = partial(print_error, status=status)
    failure_prelude = (
        f":cross_mark: [red]Failed[/red] to unstake {amount} on Netuid {netuid}"
    )

    if status:
        status.update(
            f"\n:satellite: Unstaking {amount} from {hotkey_ss58} on netuid: {netuid} ..."
        )

    block_hash = await subtensor.substrate.get_chain_head()

    current_balance, next_nonce, current_stake = await asyncio.gather(
        subtensor.get_balance(wallet.coldkeypub.ss58_address, block_hash),
        subtensor.substrate.get_account_next_index(wallet.coldkeypub.ss58_address),
        subtensor.get_stake(
            hotkey_ss58=hotkey_ss58,
            coldkey_ss58=wallet.coldkeypub.ss58_address,
            netuid=netuid,
        ),
    )

    call = await subtensor.substrate.compose_call(
        call_module="SubtensorModule",
        call_function="remove_stake_limit",
        call_params={
            "hotkey": hotkey_ss58,
            "netuid": netuid,
            "amount_unstaked": amount.rao,
            "limit_price": price_limit,
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
                status=status,
            )
            return
        else:
            err_out(
                f"\n{failure_prelude} with error: {format_error_message(e)}"
            )
        return

    await response.process_events()
    if not await response.is_success:
        err_out(
            f"\n{failure_prelude} with error: {format_error_message(await response.error_message)}"
        )
        return

    block_hash = await subtensor.substrate.get_chain_head()
    new_balance, new_stake = await asyncio.gather(
        subtensor.get_balance(wallet.coldkeypub.ss58_address, block_hash),
        subtensor.get_stake(
            hotkey_ss58=hotkey_ss58,
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
    if allow_partial_stake and (amount_unstaked != amount):
        console.print(
            "Partial unstake transaction. Unstaked:\n"
            f"  [{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]{amount_unstaked.set_unit(netuid=netuid)}[/{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}] "
            f"instead of "
            f"[blue]{amount}[/blue]"
        )

    console.print(
        f"Subnet: [{COLOR_PALETTE['GENERAL']['SUBHEADING']}]{netuid}[/{COLOR_PALETTE['GENERAL']['SUBHEADING']}] "
        f"Stake:\n  [blue]{current_stake}[/blue] :arrow_right: [{COLOR_PALETTE['STAKE']['STAKE_AMOUNT']}]{new_stake}"
    )

