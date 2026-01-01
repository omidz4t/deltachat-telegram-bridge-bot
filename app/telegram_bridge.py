import asyncio
import os
import logging
from pathlib import Path
from telethon import TelegramClient, events, utils
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ReadMentionsRequest
from deltachat2 import MsgData, Rpc
from logger import logger
from models.message import Message
from config_utils import save_config

class TelegramBridge:
    def __init__(self, config, rpc: Rpc, msg_repo=None, chan_repo=None):
        t_config = config.get('telegram', {})
        self.api_id = t_config.get('api_id')
        self.api_hash = t_config.get('api_hash')
        self.phone = t_config.get('phone')
        self.config = config
        self.rpc = rpc
        self.client = None
        self.msg_repo = msg_repo
        self.chan_repo = chan_repo
        self.media_dir = Path("data/media")
        self.media_dir.mkdir(exist_ok=True, parents=True)
        self.loop = None

        # Device info
        self.device_model = t_config.get('device_model')
        self.system_version = t_config.get('system_version')
        self.app_version = t_config.get('app_version')
        self.lang_code = t_config.get('lang_code', 'en')
        self.system_lang_code = t_config.get('system_lang_code', 'en')
        
        self.channels_to_mirror = config.get("channels_to_mirror", [])
        if not self.channels_to_mirror and "out_channel" in config:
            self.channels_to_mirror = [config["out_channel"]]

    async def _resolve_and_join_channel(self, channel_cfg, accid, sync_info_now=False):
        tgid = channel_cfg.get('tgid')
        username = channel_cfg.get('username')
        dc_chat_id = channel_cfg.get('chat_id')
        photo_mode = channel_cfg.get('channel_photo_mode', 'manual')
        
        # Prioritize username for public channels as it's easier to resolve for joining
        target_chat = username or tgid
        if not target_chat:
            logger.warning(f"No tgid or username for channel config: {channel_cfg}")
            return None
            
        if isinstance(target_chat, str) and (target_chat.startswith('-') or target_chat.isdigit()):
            try:
                target_chat = int(target_chat)
            except ValueError:
                pass

        try:
            entity = await self.client.get_entity(target_chat)
            
            # Ensure member
            if getattr(entity, 'left', False):
                logger.info(f"Joining Telegram channel: {target_chat}")
                await self.client(JoinChannelRequest(entity))
            
            actual_tg_id = utils.get_peer_id(entity)
            if channel_cfg.get('tgid') != actual_tg_id:
                logger.info(f"Updating tgid for {target_chat}: {channel_cfg.get('tgid')} -> {actual_tg_id}")
                channel_cfg['tgid'] = actual_tg_id
                save_config(self.config)

            if sync_info_now or photo_mode == 'auto':
                await self.sync_channel_info(entity, dc_chat_id, accid)
            
            return actual_tg_id
        except Exception as e:
            logger.error(f"Could not resolve/join entity for {target_chat}: {e}")
            return None

    async def run(self):
        if not self.api_id or not self.api_hash:
            logger.error("Telegram API ID or Hash not provided in config.yml. Skipping Telegram bridge.")
            return

        logger.info("Starting Telegram client (Bridge)...")
        self.client = TelegramClient(
            'data/deltabot', 
            self.api_id, 
            self.api_hash,
            device_model=self.device_model,
            system_version=self.system_version,
            app_version=self.app_version,
            lang_code=self.lang_code,
            system_lang_code=self.system_lang_code
        )
        
        await self.client.start(phone=self.phone)
        self.loop = asyncio.get_running_loop()
        
        accid = self.config.get('active_accid')
        
        tg_to_dc_map = {}
        target_chats = []

        for channel_cfg in self.channels_to_mirror:
            dc_chat_id = channel_cfg.get('chat_id')
            actual_tg_id = await self._resolve_and_join_channel(channel_cfg, accid)
            if actual_tg_id:
                tg_to_dc_map[actual_tg_id] = channel_cfg
                target_chats.append(actual_tg_id)

        if not target_chats:
            logger.error("No valid Telegram channels to mirror.")
            return
            
        await self.start_listening(target_chats, tg_to_dc_map, accid)

    async def sync_channel_info(self, entity, dc_chat_id, accid):
        try:
            tg_name = getattr(entity, 'title', None)
            logger.info(f"Checking for channel info updates from Telegram: {tg_name or entity.id}")
            
            # Get current DC chat info
            dc_chat = self.rpc.get_basic_chat_info(accid, dc_chat_id)
            dc_name = dc_chat.name
            
            # Update name if different
            if tg_name and tg_name != dc_name:
                logger.info(f"Updating Delta Chat channel name: {dc_name} -> {tg_name}")
                self.rpc.set_chat_name(accid, dc_chat_id, tg_name)
            
            # Update avatar if different
            if entity.photo:
                try:
                    avatar_path = await self.client.download_profile_photo(entity, file=f"data/tg_avatar_{entity.id}.png")
                    if avatar_path:
                        logger.info(f"Synchronizing Delta Chat channel avatar from Telegram for {tg_name}")
                        self.rpc.set_chat_profile_image(accid, dc_chat_id, str(Path(avatar_path).absolute()))
                except Exception as e:
                    logger.warning(f"Could not sync avatar: {e}")
        except Exception as e:
            logger.warning(f"General error in sync_channel_info: {e}")

    async def start_listening(self, target_chats, tg_to_dc_map, accid):
        @self.client.on(events.ChatAction(chats=target_chats))
        async def chat_action_handler(event):
            if event.new_photo or event.new_title:
                try:
                    tg_id = event.chat_id
                    channel_cfg = tg_to_dc_map.get(tg_id)
                    if channel_cfg:
                        dc_chat_id = channel_cfg.get('chat_id')
                        logger.info(f"Telegram channel update detected (photo/title change) for {tg_id}")
                        entity = await event.get_chat()
                        await self.sync_channel_info(entity, dc_chat_id, accid)
                except Exception as e:
                    logger.error(f"Error handling real-time Telegram update: {e}")

        @self.client.on(events.NewMessage(chats=target_chats))
        async def handler(event):
            try:
                tg_id = event.chat_id
                channel_cfg = tg_to_dc_map.get(tg_id)
                if not channel_cfg:
                    return
                dc_chat_id = channel_cfg.get('chat_id')
                
                photo_cfg = channel_cfg.get('photo', {})
                photo_enabled = photo_cfg.get('enable', True)
                photo_prefix = photo_cfg.get('message', '[Photo]')
                
                video_cfg = channel_cfg.get('video', {})
                video_enabled = video_cfg.get('enable', True)
                video_prefix = video_cfg.get('message', '[Video]')

                await self.client.send_read_acknowledge(event.chat_id, event.message)
                await self._relay_message(event.message, channel_cfg, accid)
                        
            except Exception as e:
                logger.error(f"Error in Telegram handler: {e}")

        logger.info(f"Telegram bridge is listening on {len(target_chats)} channels...")
        await self.client.run_until_disconnected()

    async def _relay_message(self, message, channel_cfg, accid):
        try:
            dc_chat_id = channel_cfg.get('chat_id')
            if not dc_chat_id:
                return None
            
            # Check if channel is enabled in DB
            if self.chan_repo:
                chan = self.chan_repo.get_by_chat_id(accid, dc_chat_id)
                if chan and not chan.enabled:
                    logger.debug(f"Relay disabled for channel {dc_chat_id}, skipping message.")
                    return None
            
            photo_cfg = channel_cfg.get('photo', {})
            photo_enabled = photo_cfg.get('enable', True)
            photo_prefix = photo_cfg.get('message', '[Photo]')
            
            video_cfg = channel_cfg.get('video', {})
            video_enabled = video_cfg.get('enable', True)
            video_prefix = video_cfg.get('message', '[Video]')

            text = message.message
            media_path = None
            media_type = "text"
            
            if message.photo:
                media_type = "image"
                if photo_enabled:
                    media_path = await message.download_media(file=str(self.media_dir))
                else:
                    text = f"{photo_prefix} {text}" if text else photo_prefix
            elif message.video:
                media_type = "video"
                if video_enabled:
                    media_path = await message.download_media(file=str(self.media_dir))
                else:
                    text = f"{video_prefix} {text}" if text else video_prefix
            elif message.file:
                # Handle other file types (stickers, documents, audio, etc.)
                media_path = await message.download_media(file=str(self.media_dir))
                media_type = "file"
            
            if not (text or media_path):
                logger.debug(f"Skipping message {message.id} - no supported content (text or media)")
                return None

            sender = await message.get_sender()
            sender_name = utils.get_display_name(sender) if sender else None
            
            # Handle replies/quotes
            quoted_message_id = None
            reply_to_msg_id = message.reply_to_msg_id
            if reply_to_msg_id and self.msg_repo:
                quoted_msg = self.msg_repo.get_by_telegram_id(reply_to_msg_id, dc_chat_id)
                if quoted_msg:
                    quoted_message_id = quoted_msg.dc_msg_id
            
            logger.info(f"Relaying from Telegram to DC {dc_chat_id}: {text[:30] if text else '[Media]'}...")
            
            dc_msg_id = None
            try:
                if media_path:
                    dc_msg_id = self.rpc.send_msg(accid, dc_chat_id, MsgData(
                        text=text, 
                        file=str(Path(media_path).absolute()), 
                        override_sender_name=sender_name,
                        quoted_message_id=quoted_message_id
                    ))
                else:
                    dc_msg_id = self.rpc.send_msg(accid, dc_chat_id, MsgData(
                        text=text, 
                        override_sender_name=sender_name,
                        quoted_message_id=quoted_message_id
                    ))
            except Exception as e:
                logger.error(f"Failed to relay message to Delta Chat: {e}", exc_info=(logger.level <= logging.DEBUG))

            if dc_msg_id and self.msg_repo:
                db_msg = Message(
                    telegram_msg_id=message.id,
                    dc_msg_id=dc_msg_id,
                    dc_chat_id=dc_chat_id,
                    text=text,
                    media_path=media_path,
                    media_type=media_type
                )
                self.msg_repo.save(db_msg)
            return dc_msg_id
        except Exception as e:
            logger.error(f"Error in _relay_message: {e}")
            return None

    async def fetch_history(self, tgid, limit=10, accid=None):
        if not accid:
            accid = self.config.get('active_accid')
            
        # Try to convert tgid to int if it's a string representing an ID
        original_tgid = tgid
        if isinstance(tgid, str) and (tgid.startswith('-') or tgid.isdigit()):
            try:
                tgid = int(tgid)
            except ValueError:
                pass

        # Find channel_cfg
        channel_cfg = None
        for cfg in self.channels_to_mirror:
            cfg_tgid = cfg.get('tgid')
            if isinstance(cfg_tgid, str) and (cfg_tgid.startswith('-') or cfg_tgid.isdigit()):
                try:
                    cfg_tgid = int(cfg_tgid)
                except:
                    pass
            
            if cfg_tgid == tgid or cfg.get('username') == original_tgid:
                channel_cfg = cfg
                break
        
        if not channel_cfg:
            logger.warning(f"No mirror configuration for {tgid}")
            return
        
        dc_chat_id = channel_cfg.get('chat_id')
        if dc_chat_id and self.chan_repo:
            chan = self.chan_repo.get_by_chat_id(accid, dc_chat_id)
            if chan and not chan.enabled:
                logger.info(f"History fetch disabled for channel {dc_chat_id}, skipping.")
                return

        logger.info(f"Fetching last {limit} messages from Telegram for {tgid}...")
        try:
            entity = await self.client.get_entity(tgid)
            tg_messages = []
            # Scan more than limit to account for unbridgeable service messages
            # and ensure we get enough content.
            async for msg in self.client.iter_messages(entity, limit=limit * 2):
                # Only count messages that have bridgeable content (text or media)
                if msg.message or msg.photo or msg.video or msg.file:
                    tg_messages.append(msg)
                    if len(tg_messages) >= limit:
                        break
            
            # Sort messages from oldest to newest for chronological relay
            tg_messages.reverse()
            
            count = 0
            pending_resend_ids = []

            async def flush_resends():
                nonlocal count
                if pending_resend_ids:
                    logger.info(f"Resending {len(pending_resend_ids)} existing messages to {tgid}...")
                    try:
                        self.rpc.resend_messages(accid, pending_resend_ids)
                        count += len(pending_resend_ids)
                    except Exception as e:
                        logger.warning(f"Failed to resend batch for {tgid}: {e}")
                    pending_resend_ids.clear()

            for msg in tg_messages:
                existing = self.msg_repo.get_by_telegram_id(msg.id, dc_chat_id) if self.msg_repo else None
                valid_id = None
                if existing and existing.dc_msg_id and existing.dc_chat_id == dc_chat_id:
                    try:
                        self.rpc.get_message(accid, existing.dc_msg_id)
                        valid_id = existing.dc_msg_id
                    except:
                        pass
                
                if valid_id:
                    pending_resend_ids.append(valid_id)
                else:
                    await flush_resends()
                    logger.info(f"Message {msg.id} missing in DC (or new), relaying...")
                    dc_msg_id = await self._relay_message(msg, channel_cfg, accid)
                    if dc_msg_id:
                        count += 1
            
            await flush_resends()
            
            if count > 0:
                logger.info(f"Handled {count} history messages for {tgid}.")
            else:
                logger.info("No history messages to handle.")
        except Exception as e:
            logger.error(f"Failed to fetch history for {tgid}: {e}")

def start_telegram_bridge(config, rpc, msg_repo=None, chan_repo=None, bridge_container=None):
    bridge = TelegramBridge(config, rpc, msg_repo, chan_repo)
    if bridge_container is not None:
        bridge_container['bridge'] = bridge
    asyncio.run(bridge.run())

async def init_telegram_session_async(config):
    t_config = config.get('telegram', {})
    api_id = t_config.get('api_id')
    api_hash = t_config.get('api_hash')
    phone = t_config.get('phone')
    
    if not api_id or not api_hash:
        logger.error("Telegram API ID or Hash not provided in config.yml.")
        return False
        
    logger.info("Initializing Telegram session...")
    client = TelegramClient(
        'data/deltabot', 
        api_id, 
        api_hash,
        device_model=t_config.get('device_model'),
        system_version=t_config.get('system_version'),
        app_version=t_config.get('app_version'),
        lang_code=t_config.get('lang_code', 'en'),
        system_lang_code=t_config.get('system_lang_code', 'en')
    )
    await client.start(phone=phone)
    logger.info("Telegram session initialized successfully.")
    await client.disconnect()
    return True

def init_telegram_session(config):
    return asyncio.run(init_telegram_session_async(config))

async def sync_tg_info_to_dc_async(config, rpc):
    t_config = config.get('telegram', {})
    api_id = t_config.get('api_id')
    api_hash = t_config.get('api_hash')
    
    if not api_id or not api_hash:
        return

    async with TelegramClient(
        'data/deltabot', 
        api_id, 
        api_hash,
        device_model=t_config.get('device_model'),
        system_version=t_config.get('system_version'),
        app_version=t_config.get('app_version'),
        lang_code=t_config.get('lang_code', 'en'),
        system_lang_code=t_config.get('system_lang_code', 'en')
    ) as client:
        bridge = TelegramBridge(config, rpc)
        bridge.client = client
        
        accid = config.get('active_accid')
        for channel_cfg in bridge.channels_to_mirror:
            await bridge._resolve_and_join_channel(channel_cfg, accid, sync_info_now=True)

def sync_tg_info_to_dc(config, rpc):
    asyncio.run(sync_tg_info_to_dc_async(config, rpc))

