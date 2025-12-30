import sys
import os
import argparse
import yaml
import time
import getpass
import logging
import signal
from threading import Thread
from pathlib import Path
from typing import Optional

from deltachat2 import Bot, Rpc, IOTransport, EventType, CoreEvent, Event, MsgData, events, JsonRpcError
from deltachat2.events import RawEvent, HookCollection

from logger import logger
from repository.channel_repository import ChannelRepository
from repository.message_repository import MessageRepository
from models.channel import Channel
from db import init_db
from telegram_bridge import start_telegram_bridge, init_telegram_session, sync_tg_info_to_dc

from config_utils import load_config, save_config

def process_init_events(bot: Bot):
    events_to_log = (EventType.INFO, EventType.WARNING, EventType.ERROR)
    last_progress = -1
    while True:
        try:
            raw_event = bot.rpc.get_next_event()
            accid = raw_event.context_id
            event = CoreEvent(raw_event.event)
            comment = getattr(event, 'comment', None)
            
            if event.kind == EventType.CONFIGURE_PROGRESS:
                if event.progress != last_progress:
                    logger.info(f"Configuration progress: {event.progress / 10}%")
                    last_progress = event.progress
                if comment:
                    logger.info(comment)
            elif event.kind in events_to_log:
                msg = f"[acc={accid}] {comment or event.kind}"
                if event.kind == EventType.ERROR:
                    logger.error(f"Configuration Error: {msg}")
                    break
                elif event.kind == EventType.WARNING:
                    logger.warning(msg)
                else:
                    logger.info(msg)
            
            if last_progress >= 1000 or (event.kind == EventType.CONFIGURE_PROGRESS and event.progress >= 1000):
                break
        except Exception as e:
            logger.error(f"Error in event processing: {e}")
            break

def init_account(bot: Bot, addr: str):
    accid = bot.rpc.add_account()
    logger.info(f"Starting configuration process for account {accid}...")
    bot.rpc.set_config(accid, "bot", "1")
    
    task = Thread(target=process_init_events, args=(bot,), daemon=True)
    task.start()
    
    try:
        if "dcaccount:" in addr.lower():
            bot.rpc.add_transport_from_qr(accid, addr)
        else:
            password = getpass.getpass(f"Enter password for {addr}: ")
            params = {"addr": addr, "password": password}
            bot.rpc.add_or_update_transport(accid, params)
        task.join()
    except JsonRpcError as err:
        logger.error(err)
    
    if bot.rpc.is_configured(accid):
        logger.info(f"Account {accid} configured successfully.")
        return accid
    else:
        logger.error("Configuration failed or still in progress.")
        sys.exit(1)

def setup_channel(bot: Bot, accid: int, channel_cfg: dict) -> int:
    name = channel_cfg.get("name", channel_cfg.get("username", "Telegram Bridge Channel"))
    avatar = channel_cfg.get("avatar")
    chat_id = channel_cfg.get("chat_id")
    
    if chat_id:
        try:
            bot.rpc.get_basic_chat_info(accid, chat_id)
            logger.info(f"Using existing broadcast channel {chat_id} for {name}.")
            # bot.rpc.set_chat_name(accid, chat_id, name)
        except JsonRpcError:
            logger.warning(f"Channel {chat_id} not found in database. Creating a new one.")
            chat_id = None

    if not chat_id:
        logger.info(f"Creating new broadcast channel: {name}")
        chat_id = bot.rpc.create_broadcast(accid, name)
        # Force visibility to Normal to ensure it's syncable
        try:
            bot.rpc.set_chat_visibility(accid, chat_id, "Normal")
        except:
            pass
        
        channel_cfg["chat_id"] = chat_id
        if channel_cfg.get("send_start", False):
            # Initial promotion
            bot.rpc.send_msg(accid, chat_id, MsgData(text="start"))
    else:
        # Ensure it's visible even if it existed
        try:
            bot.rpc.set_chat_visibility(accid, chat_id, "Normal")
        except:
            pass
    
    if avatar:
        avatar_path = Path(avatar)
        if avatar_path.exists():
            logger.info(f"Setting channel avatar from: {avatar}")
            bot.rpc.set_chat_profile_image(accid, chat_id, str(avatar_path.absolute()))
        else:
            logger.warning(f"Avatar file not found: {avatar}")
            
    return chat_id

def run_bot(rpc: Rpc, hooks: HookCollection):
    config = load_config()
    active_accid = config.get("active_accid")
    channels_to_mirror = config.get("channels_to_mirror", [])
    
    # Legacy support
    if not channels_to_mirror and "out_channel" in config:
        channels_to_mirror = [config["out_channel"]]
        # also need to add tgid/username if missing, but it might be hard here
    
    channel_ids = [c.get("chat_id") for c in channels_to_mirror if c.get("chat_id")]
    
    db_path = "data/db.sqlite"
    msg_repo = MessageRepository(db_path)

    history_config = config.get("history_resend", {})
    history_enabled = history_config.get("enabled", False)
    history_limit = history_config.get("limit", 10)

    last_resend_times = {} # chat_id -> timestamp
    cooldown = 10 # seconds

    @hooks.on(events.RawEvent)
    def log_membership(bot, accid, event):
        nonlocal last_resend_times
        kind = event.get("kind")
        if kind in ("SecureJoinInvite", "SecureJoinQrScanSuccess", "MemberAdded", "ChatlistItemChanged", "ContactChanged"):
            # Only log interesting events
            if kind != "ChatlistItemChanged":
                logger.debug(f"!!! EVENT: {kind} - {event}")
            
            chat_id = event.get("chat_id")
            # History resend logic
            if history_enabled and kind in ("MemberAdded", "ChatlistItemChanged") and chat_id in channel_ids:
                current_time = time.time()
                # Use cooldown to prevent infinite loops (since resending history triggers ChatlistItemChanged)
                if current_time - last_resend_times.get(chat_id, 0) < cooldown:
                    return

                logger.info(f"Potential new member join detected in chat {chat_id} ({kind}). Preparing history resend...")
                
                try:
                    # "Approve" the state - move from requests/noticed if needed
                    bot.rpc.accept_chat(accid, chat_id)
                    bot.rpc.marknoticed_chat(accid, chat_id)
                    
                    latest_msgs = msg_repo.get_latest(history_limit)
                    dc_msg_ids = [m.dc_msg_id for m in latest_msgs if m.dc_msg_id]
                    
                    if dc_msg_ids:
                        logger.info(f"Resending {len(dc_msg_ids)} messages to channel {chat_id}...")
                        bot.rpc.resend_messages(accid, dc_msg_ids)
                        last_resend_times[chat_id] = current_time
                        logger.info("History resend complete.")
                except Exception as e:
                    logger.error(f"Failed to handle history resend: {e}")

    @hooks.on(events.NewMessage)
    def handle_msg(bot, accid, event):
        msg = event.msg
        # Skip messages that are not in our broadcast channels
        if msg.chat_id not in channel_ids:
            logger.debug(f"Ignoring message in chat {msg.chat_id} (not a broadcast channel)")
            return

        msg_type = "System" if msg.is_system else "Text"
        logger.info(f"[acc={accid}] {msg_type} Message in chat {msg.chat_id}: {msg.text!r}")
        
    accounts = rpc.get_all_account_ids()
    if not accounts:
        logger.error("No accounts configured. Run --init first.")
        return

    acc_to_run = active_accid if active_accid in accounts else accounts[0]
    
    logger.info(f"Starting bot for account: {acc_to_run} (Listening on {len(channel_ids)} channels)")
    
    # Start Telegram Bridge in a separate thread, sharing the same RPC instance
    t_thread = Thread(target=start_telegram_bridge, args=(config, rpc, msg_repo), daemon=True)
    t_thread.start()

    bot = Bot(rpc, hooks, logger)
    
    for channel_cfg in channels_to_mirror:
        chat_id = channel_cfg.get("chat_id")
        if chat_id and channel_cfg.get("send_start", False):
            try:
                logger.info(f"Sending 'start' message to channel {chat_id}...")
                bot.rpc.send_msg(acc_to_run, chat_id, MsgData(text="start"))
            except Exception as e:
                logger.warning(f"Could not send startup message for {chat_id}: {e}")

    bot.run_forever(acc_to_run)

def main():
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received. Closing...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    parser = argparse.ArgumentParser(description="DeltaChat Telegram Bridge Bot")
    parser.add_argument("--init", nargs='?', const='PROMPT', help="Initialize account")
    parser.add_argument("--link", action="store_true", help="Show invite link and setup channel")
    parser.add_argument("--run", action="store_true", help="Run the bot")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    db_path = "data/db.sqlite"
    init_db(db_path)
    
    accounts_dir = str((data_dir / "accounts").absolute())
    
    hooks = HookCollection()
    
    try:
        with IOTransport(accounts_dir=accounts_dir) as trans:
            rpc = Rpc(trans)
            
            if args.init:
                bot = Bot(rpc, hooks, logger)
                config = load_config()
                
                channels_to_mirror = config.get("channels_to_mirror", [])
                if not channels_to_mirror and "out_channel" in config:
                    channels_to_mirror = [config["out_channel"]]
                
                accounts_config = config.get("accounts", [])
                
                # Use existing account if configured and available
                accid = None
                if accounts_config:
                    first_acc = accounts_config[0]
                    if first_acc.get("use_if_exists") and first_acc.get("accid"):
                        existing_accounts = rpc.get_all_account_ids()
                        if first_acc["accid"] in existing_accounts:
                            accid = first_acc["accid"]
                            logger.info(f"Using existing account {accid}")
                
                if not accid:
                    if accounts_config and "server" in accounts_config[0]:
                        addr = f"dcaccount:{accounts_config[0]['server'].rstrip('/')}/new"
                    else:
                        addr = "dcaccount:https://nine.testrun.org/new"
                    
                    logger.info(f"Initializing new account with address: {addr}")
                    accid = init_account(bot, addr)
                    
                    if not accounts_config:
                        config["accounts"] = [{"accid": accid, "server": "https://nine.testrun.org", "use_if_exists": True}]
                    else:
                        config["accounts"][0]["accid"] = accid
                        config["accounts"][0]["use_if_exists"] = True
                
                config["active_accid"] = accid
                
                # 2. Setup DC Channels
                for channel_cfg in channels_to_mirror:
                    setup_channel(bot, accid, channel_cfg)
                
                save_config(config)
                
                # 3. Initialize Telegram Session
                init_telegram_session(config)
                
                # 4. Sync name/photo for each channel if auto
                sync_tg_info_to_dc(config, rpc)
                
                # 5. Show links
                print(f"\nSUCCESS! Delta Chat Telegram Bridge is configured.")
                for channel_cfg in channels_to_mirror:
                    chat_id = channel_cfg.get("chat_id")
                    if chat_id:
                        qrdata = rpc.get_chat_securejoin_qr_code(accid, chat_id)
                        name = channel_cfg.get("name", channel_cfg.get("username", "Unknown"))
                        print(f"\nBroadcast Channel link for '{name}' (Account #{accid}):")
                        print(qrdata)
                
                print(f"\nYou can now run the bot with: uv run python app/main.py --run")
            
            elif args.link:
                bot = Bot(rpc, hooks, logger)
                config = load_config()
                accid = config.get("active_accid")
                
                accounts = rpc.get_all_account_ids()
                if not accounts:
                    logger.error("No accounts found. Use --init first.")
                    return
                
                if not accid or accid not in accounts:
                    accid = accounts[0]
                
                if rpc.is_configured(accid):
                    channels_to_mirror = config.get("channels_to_mirror", [])
                    if not channels_to_mirror and "out_channel" in config:
                        channels_to_mirror = [config["out_channel"]]
                        
                    for channel_cfg in channels_to_mirror:
                        chat_id = setup_channel(bot, accid, channel_cfg)
                        qrdata = rpc.get_chat_securejoin_qr_code(accid, chat_id)
                        name = channel_cfg.get("name", channel_cfg.get("username", "Unknown"))
                        print(f"\nBroadcast Channel link for '{name}' (Account #{accid}):")
                        print(qrdata)
                    save_config(config)
                else:
                    logger.error(f"Account #{accid} not configured.")
            
            elif args.run:
                run_bot(rpc, hooks)
            
            else:
                parser.print_help()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

