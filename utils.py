from typing import TYPE_CHECKING, Optional
import os
from bittensor_wallet import Wallet


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