import asyncio
import os
import logging
from pathlib import Path
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ReadMentionsRequest
from deltachat2 import MsgData, Rpc
from logger import logger
from models.message import Message

class TelegramBridge:
    def __init__(self, config, rpc: Rpc, msg_repo=None):
        t_config = config.get('telegram', {})
        self.api_id = t_config.get('api_id')
        self.api_hash = t_config.get('api_hash')
        self.phone = t_config.get('phone')
        self.config = config
        self.rpc = rpc
        self.client = None
        self.msg_repo = msg_repo
        self.media_dir = Path("data/media")
        self.media_dir.mkdir(exist_ok=True, parents=True)

        # Device info
        self.device_model = t_config.get('device_model')
        self.system_version = t_config.get('system_version')
        self.app_version = t_config.get('app_version')
        self.lang_code = t_config.get('lang_code', 'en')
        self.system_lang_code = t_config.get('system_lang_code', 'en')

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
        
        in_channel = self.config.get('in_channel', {})
        bridge_channel = in_channel.get('bridge_channel')
        bridge_channel_id = in_channel.get('bridge_channel_id')
        
        try:
            target_chat = int(bridge_channel_id)
        except (ValueError, TypeError):
            target_chat = bridge_channel

        if bridge_channel:
            try:
                logger.info(f"Ensuring member of Telegram channel: {bridge_channel}")
                await self.client(JoinChannelRequest(bridge_channel))
            except Exception as e:
                logger.warning(f"Note on joining Telegram channel: {e}")

        accid = self.config.get('active_accid')
        out_channel_config = self.config.get('out_channel', {})
        dc_chat_id = out_channel_config.get('chat_id')
        photo_mode = out_channel_config.get('channel_photo_mode', 'manual')

        if not dc_chat_id:
            logger.error("No Delta Chat channel ID found in config. Run --link first.")
            return

        if photo_mode == 'auto':
            await self.sync_channel_info(target_chat, dc_chat_id, accid)
        
        await self.start_listening(target_chat, dc_chat_id, accid)

    async def sync_channel_info(self, target_chat, dc_chat_id, accid):
        try:
            logger.info(f"Checking for channel info updates from Telegram: {target_chat}")
            entity = await self.client.get_entity(target_chat)
            tg_name = getattr(entity, 'title', None)
            
            # Get current DC chat info
            dc_chat = self.rpc.get_basic_chat_info(accid, dc_chat_id)
            dc_name = dc_chat.name
            
            # Update name if different
            if tg_name and tg_name != dc_name:
                logger.info(f"Updating Delta Chat channel name: {dc_name} -> {tg_name}")
                self.rpc.set_chat_name(accid, dc_chat_id, tg_name)
            else:
                logger.debug("Channel name is already up to date.")
            
            # Sync account display name
            if tg_name:
                try:
                    logger.info(f"Setting Delta Chat account display name to: {tg_name}")
                    self.rpc.set_config(accid, "displayname", tg_name)
                except Exception as e:
                    logger.warning(f"Could not set account display name: {e}")
            
            # Update avatar if different
            if entity.photo:
                try:
                    avatar_path = await self.client.download_profile_photo(entity, file="data/tg_avatar.png")
                    if avatar_path:
                        logger.info(f"Synchronizing Delta Chat channel avatar from Telegram")
                        self.rpc.set_chat_profile_image(accid, dc_chat_id, str(Path(avatar_path).absolute()))
                        
                        # ALSO sync account profile
                        logger.info(f"Synchronizing Delta Chat account profile image from Telegram")
                        abs_path = str(Path(avatar_path).absolute())
                        # Try both ways to be sure
                        self.rpc.set_config(accid, "selfavatar", abs_path)
                        try:
                            # Contact ID 1 is always the self-contact
                            self.rpc.set_contact_profile_image(accid, 1, abs_path)
                        except:
                            pass
                except Exception as e:
                    logger.warning(f"Could not sync avatar: {e}")
        except Exception as e:
            logger.warning(f"General error in sync_channel_info: {e}")

    async def start_listening(self, target_chat, dc_chat_id, accid):
        @self.client.on(events.ChatAction(chats=target_chat))
        async def chat_action_handler(event):
            # Check config again to ensure we have latest photo_mode
            current_out_config = self.config.get('out_channel', {})
            current_photo_mode = current_out_config.get('channel_photo_mode', 'manual')
            
            if current_photo_mode != 'auto':
                return

            if event.new_photo or event.new_title:
                try:
                    logger.info(f"Telegram channel update detected (photo/title change) for {target_chat}")
                    await self.sync_channel_info(target_chat, dc_chat_id, accid)
                except Exception as e:
                    logger.error(f"Error handling real-time Telegram update: {e}")

        @self.client.on(events.NewMessage(chats=target_chat))
        async def handler(event):
            try:
                await self.client.send_read_acknowledge(event.chat_id, event.message)
                
                text = event.message.message
                media_path = None
                media_type = "text"
                
                if event.message.photo:
                    media_type = "image"
                    media_path = await event.message.download_media(file=str(self.media_dir))
                elif event.message.video:
                    media_type = "video"
                    media_path = await event.message.download_media(file=str(self.media_dir))
                
                if text or media_path:
                    logger.info(f"Relaying from Telegram: {text[:30] if text else '[Media]'}...")
                    
                    dc_msg_id = None
                    try:
                        if media_path:
                            dc_msg_id = self.rpc.send_msg(accid, dc_chat_id, MsgData(text=text, file=str(Path(media_path).absolute())))
                        else:
                            dc_msg_id = self.rpc.send_msg(accid, dc_chat_id, MsgData(text=text))
                    except Exception as e:
                        logger.error(f"Failed to relay message to Delta Chat: {e}")

                    if self.msg_repo:
                        db_msg = Message(
                            telegram_msg_id=event.message.id,
                            dc_msg_id=dc_msg_id,
                            text=text,
                            media_path=media_path,
                            media_type=media_type
                        )
                        self.msg_repo.save(db_msg)
                        
            except Exception as e:
                logger.error(f"Error in Telegram handler: {e}")

        logger.info(f"Telegram bridge is listening on {target_chat}...")
        await self.client.run_until_disconnected()

def start_telegram_bridge(config, rpc, msg_repo=None):
    t_config = config.get('telegram', {})
    api_id = t_config.get('api_id')
    api_hash = t_config.get('api_hash')
    phone = t_config.get('phone')
    
    # Use the shared RPC instance. deltachat2 RPC is thread-safe as it uses
    # separate request IDs and a dedicated reader thread for responses.
    bridge = TelegramBridge(config, rpc, msg_repo)
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
    in_channel = config.get('in_channel', {})
    out_channel = config.get('out_channel', {})
    
    api_id = t_config.get('api_id')
    api_hash = t_config.get('api_hash')
    
    bridge_channel_id = in_channel.get('bridge_channel_id')
    bridge_channel = in_channel.get('bridge_channel')
    try:
        target_chat = int(bridge_channel_id)
    except (ValueError, TypeError):
        target_chat = bridge_channel

    dc_chat_id = out_channel.get('chat_id')
    accid = config.get('active_accid')
    
    if not all([api_id, api_hash, target_chat, dc_chat_id, accid]):
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
        await bridge.sync_channel_info(target_chat, dc_chat_id, accid)

def sync_tg_info_to_dc(config, rpc):
    asyncio.run(sync_tg_info_to_dc_async(config, rpc))

