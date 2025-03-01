import bittensor as bt
from bittensor_cli.src.bittensor.balances import Balance

import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import argparse

from utils import wallet_ask
# 配置日志
logging.basicConfig(
    level=logging.INFO,               # 设置日志级别为 INFO，这样 INFO 级别以上的日志会被记录
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

def get_registered_subnets(subtensor):
    metagraph = subtensor.all_subnets()
    if metagraph is None:
        return set()  # Return empty set if querying fails
    else:
        logging.info(f"All subnets: {len(metagraph)}")
    logging.info(f"Latest subnet: {metagraph[-1]}")
    return len(metagraph), metagraph[-1]

def send_email(subject, body, to_email, from_email, password):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    try:
        server.login(from_email, password)
        message = MIMEMultipart()
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        server.sendmail(from_email, to_email, message.as_string())
        logging.info(f"Email sent to {to_email}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
    finally:
        server.quit()

def monitor_new_subnet_registrations(network="finney", check_interval=60, email=None, from_email=None, password=None, wallet=None):
    subtensor = bt.subtensor(network=network)
    logging.info(f"Connected to Bittensor network: {network}")

    previous_subnets, _ = get_registered_subnets(subtensor)
    logging.info(f"Previous number of registered subnets: {previous_subnets}")
    
    while True:
        try:
            current_subnets, latest_one = get_registered_subnets(subtensor)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            new_subnets = current_subnets - previous_subnets
            if new_subnets > 0:
                logging.info(f"[{current_time}] New subnets detected: {latest_one}")
                logging.info(f"Total registered subnets: {current_subnets}")

                if email:
                    subject = f"New Subnet Registered: {latest_one}"
                    body = f"New subnet {latest_one} detected at {current_time}. Total subnets: {current_subnets}"
                    send_email(subject, body, email, from_email, password)
                
                while True:
                    logging.info(f"Starting to register to new subnet!!!!!!!!!")
                    netuid = current_subnets - 1
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
                    if 1.1 < current_recycle.tao:
                        logging.error(
                            f"Exceed the max_cost Current recycle is {current_recycle} TAO")
                        return
                    
                    done = subtensor.burned_register(
                        wallet=wallet,
                        netuid=netuid
                    )
                    if done:
                        logging.info("Landing Success!!!")
                        break
            else:
                logging.info(f"[{current_time}] No new subnets detected. Total: {current_subnets}")

            previous_subnets = current_subnets
            time.sleep(check_interval)

        except Exception as e:
            logging.error(f"Error occurred: {e}")
            time.sleep(check_interval)

if __name__ == "__main__":
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description="Monitor new subnet registrations on Bittensor network.")
    parser.add_argument("--network", type=str, default="finney", help="Network to monitor (finney, test, local).")
    parser.add_argument("--check_interval", type=int, default=60, help="Time interval between checks in seconds.")
    parser.add_argument("--to_send", type=str, required=True, help="Target email address to receive notifications.")
    parser.add_argument("--from_email", type=str, required=True, help="Sender email address (Gmail).")
    parser.add_argument("--password", type=str, required=True, help="Gmail application-specific password.")
    parser.add_argument("--wallet_name", type=str, required=True, help="wallet coldkey name")
    parser.add_argument("--wallet_path", type=str, default="~/.bittensor/wallets", help='Path to wallet (default: ~/.bittensor/wallets)')
    parser.add_argument("--hotkey", type=str, required=True, help="The hotkey name u want to use to register")
    parser.add_argument("--wallet_password", type=str, required=True, help="Password for wallet")
    args = parser.parse_args()

    # 调用主函数
    logging.info(f"Starting subnet registration monitor on {args.network} network...")
    wallet = wallet_ask(
            args.wallet_name,
            args.wallet_path,
            args.hotkey
        )
    wallet.coldkey_file.save_password_to_env(args.wallet_password)
    wallet.unlock_coldkey()

    monitor_new_subnet_registrations(
        network=args.network,
        check_interval=args.check_interval,
        email=args.to_send,
        from_email=args.from_email,
        password=args.password,
        wallet=wallet
    )