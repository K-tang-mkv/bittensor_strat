# bittensor_strat
* auto_sell when alpha > 1 TAO
* auto register

## Usage
1. auto trading
```bash
screen -S auto_trading # open a background shell
python auto_buy_and_sell.py --wallet_name <your_wallet_name> --hotkey <hotkey_name> --netuid <id>
```

2. auto register

```
screen -S auto_reg

python auto_register.py --wallet_name coldkey_name --hotkey hotkey --netuid 69 --max_allowed_cost 1.1
```

3. monitor new subnet
```
nohup python monitor_newsubnet.py --to_send dest@gmail.com --from_email sender@gmail.com --password "**" > log &
```