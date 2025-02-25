# bittensor_strat
* auto_sell when alpha > 1 TAO
* auto register
* monitor_new subnet
* check balance

## Usage
1. auto trading
```bash
python auto_buy_and_sell.py --wallet_name <your_wallet_name> --hotkey <hotkey_name> --netuid <id> --password <>
```

2. auto register

```
python auto_register.py --wallet_name coldkey_name --hotkey hotkey --netuid 69 --max_allowed_cost 1.1 --password <>
```

3. monitor new subnet
```
nohup python monitor_newsubnet.py --to_send dest@gmail.com --from_email sender@gmail.com --password "**" > log &
```

4. check TAO balance
```
python check_balance.py --wallet_name coldkey_name
```

**TODO:**  
	1.	Monitor for new subnets, check the registration fee, and automatically register if it’s less than 1 TAO.  
	2.	Immediately buy into the subnet’s alpha, monitor the profit, and exit with the original capital once it doubles.