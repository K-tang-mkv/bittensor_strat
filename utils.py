from typing import TYPE_CHECKING, Optional
import os
from bittensor_wallet import Wallet
from bittensor_cli.src.bittensor.balances import Balance


def wallet_ask(
        wallet_name: Optional[str],
        wallet_path: Optional[str],
        wallet_hotkey: Optional[str],
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
