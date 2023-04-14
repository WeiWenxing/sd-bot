import logging
import itertools
import datetime
from PIL import Image, PngImagePlugin
from io import BytesIO

import telegram
from telegram import constants, BotCommandScopeAllGroupChats
from telegram import Message, MessageEntity, Update, \
    BotCommand, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, \
    filters, InlineQueryHandler, Application, CallbackContext, CallbackQueryHandler

from webuiapi_helper import WebUIApiHelper, byteBufferOfImage, saveImage


def message_text(message: Message) -> str:
    """
    Returns the text of a message, excluding any bot commands.
    """
    message_text = message.text
    if message_text is None:
        return ''

    for _, text in sorted(message.parse_entities([MessageEntity.BOT_COMMAND]).items(), key=(lambda item: item[0].offset)):
        message_text = message_text.replace(text, '').strip()

    return message_text if len(message_text) > 0 else ''


class SDBot:
    """
    Class representing a ChatGPT Telegram Bot.
    """

    def __init__(self, config: dict, api: WebUIApiHelper):
        """
        Initializes the bot with the given configuration and GPT bot object.
        :param config: A dictionary containing the bot configuration
        :param api: WebUIApiHelper object
        """
        self.config = config
        self.webapihelper = api
        self.commands = [
            BotCommand(command='help', description='Show help message'),
            BotCommand(command='draw', description='draw a picture'),
            BotCommand(command='model', description='change models'),
            BotCommand(command='dress', description='change clothes'),
        ]
        self.group_commands = [
            BotCommand(command='chat', description='Chat with the bot!')
        ] + self.commands
        self.disallowed_message = "Sorry, you are not allowed to use this bot. You can connect to @aipicfree"
        self.budget_limit_message = "Sorry, you have reached your monthly usage limit."
        self.usage = {}
        self.last_message = {}

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        commands = self.group_commands if self.is_group_chat(update) else self.commands
        commands_description = [f'/{command.command} - {command.description}' for command in commands]
        help_text = 'I\'m a SD bot, talk to me!' + \
                    '\n\n' + \
                    '\n'.join(commands_description) + \
                    '\n\n' + \
                    'Send me a image and I\'ll transcribe it for you!'
        await update.message.reply_text(help_text, disable_web_page_preview=True)

    async def draw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        await update.message.reply_text("draw")


    async def show_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        keyboard = [
            [
                InlineKeyboardButton("GF2", callback_data="GuoFeng2"),
                InlineKeyboardButton("GF3.2", callback_data="GuoFeng3.2"),
                InlineKeyboardButton("chill", callback_data="chilloutmix_NiPrunedFp32Fix"),
                InlineKeyboardButton("GF3.2Inp", callback_data="GuoFeng3.2Inpainting.inpainting"),
                InlineKeyboardButton("ubInp", callback_data="uberRealisticPornMerge_urpmv13Inpainting"),
            ],
            #[InlineKeyboardButton("Option 3", callback_data="3")],
        ]

        old_model = self.webapihelper.api.util_get_current_model()
        logging.info(old_model)

        # get list of available models
        logging.info("refresh checkpoints")
        self.webapihelper.api.refresh_checkpoints()
        logging.info("refresh checkpoints end")
        models = self.webapihelper.api.util_get_model_names()
        logging.info(models)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"cur model: {old_model}\nchange model: ", reply_markup=reply_markup)

    async def set_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        logging.info(query)
        model = query.data
        logging.info(model)
        message = query.message
        logging.info(message)

        # CallbackQueries need to be answered, even if no notification to the user is needed
        await query.answer()
        # 获取原始消息对象
        K = await message.reply_text("Please Wait 1-2 Minutes")
        # set model (find closest match)
        self.webapihelper.api.util_set_model(f'{model}')
        # wait for job complete
        self.webapihelper.api.util_wait_for_ready()

        await K.delete()

        await message.reply_text("change checkpoints end")

    async def show_dress(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        keyboard = [
            [
                InlineKeyboardButton("礼服", callback_data="see-through:evening dress, bare shoulders,"),
                InlineKeyboardButton("旗袍", callback_data="see-through, cheongsam,"),
                InlineKeyboardButton("国风", callback_data="hanfu, sheer tulle, see-through,"),
                InlineKeyboardButton("婚纱", callback_data="wedding dress"),
                InlineKeyboardButton("泳装", callback_data="bikini"),
            ],
            [
                InlineKeyboardButton("运动服", callback_data="sportswear"),
                InlineKeyboardButton("铠甲", callback_data="armor,"),
                InlineKeyboardButton("内衣", callback_data="hot underware,"),
                InlineKeyboardButton("制服", callback_data="police_uniform,"),
                InlineKeyboardButton("学院", callback_data="school_uniform,"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.webapihelper.cache_image = await self.getImgFromMsg(context.bot, update.message)
        await update.message.reply_text("change clothes: ", reply_markup=reply_markup)

    async def draw_dress(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        logging.info(query)
        clothes = query.data
        logging.info(clothes)
        message = query.message
        logging.info(message)
        bot = context.bot

        # CallbackQueries need to be answered, even if no notification to the user is needed
        await query.answer()

        if self.webapihelper.cache_image is not None:
            result = self.webapihelper.clothes_op(self.webapihelper.cache_image, clothes, 60.0)
            for img in result.images:
                await bot.send_photo(message.chat.id, photo=byteBufferOfImage(img, 'JPEG'), caption=f'{clothes}')
        else:
            logging.info("no photo!")

    async def show_bg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        keyboard = [
            [
                InlineKeyboardButton("海边", callback_data="sea beach,"),
                InlineKeyboardButton("草地", callback_data="grassland,"),
                InlineKeyboardButton("太空", callback_data="space,"),
                InlineKeyboardButton("山脉", callback_data="mountain,"),
                InlineKeyboardButton("街道", callback_data="street,"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.webapihelper.cache_image = await self.getImgFromMsg(context.bot, update.message)
        await update.message.reply_text("change background: ", reply_markup=reply_markup)

    async def draw_bg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        logging.info(query)
        bg = query.data
        logging.info(bg)
        message = query.message
        logging.info(message)
        bot = context.bot

        # CallbackQueries need to be answered, even if no notification to the user is needed
        await query.answer()

        if self.webapihelper.cache_image is not None:
            result = self.webapihelper.bg_op(self.webapihelper.cache_image, bg)
            for img in result.images:
                type_mode = 'PNG' if img.mode == "RGBA" else 'JPEG'
                await bot.send_photo(message.chat.id, photo=byteBufferOfImage(img, type_mode), caption=f'{bg}')
        else:
            logging.info("no photo!")

    async def getImgFromMsg(self, bot, message):
        logging.info("Message contains one photo.")
        date = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')
        path = f'download/clothes_{date}.jpg'
        logging.info(f"{path}")
        file = await bot.getFile(message.photo[-1].file_id)
        logging.info(file)
        photo_path = await file.download_to_drive(custom_path=path)
        logging.info(photo_path)
        with open(photo_path, "rb") as f:
            file_bytes = f.read()
        img_ori = Image.open(BytesIO(file_bytes))
        return img_ori

    async def trip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        message = update.message
        bot = context.bot
        if message.photo:
            logging.info("Message contains one photo.")
            date = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')
            path = f'download/photo_{date}.jpg'
            logging.info(f"{path}")
            file = await bot.getFile(message.photo[-1].file_id)
            logging.info(file)
            photo_path = await file.download_to_drive(custom_path=path)
            logging.info(photo_path)

            with open(photo_path, "rb") as f:
                file_bytes = f.read()
            img_ori = Image.open(BytesIO(file_bytes))

            for i in range(1):
                result = self.webapihelper.nude_op(img_ori)
                logging.info(f"=============================nude {i}===============================")
                await message.reply_photo(byteBufferOfImage(result.image, 'JPEG'))
            #     await message.reply_photo(byteBufferOfImage(result.images[1], 'PNG'))
            #     await message.reply_photo(byteBufferOfImage(result.images[2], 'JPEG'))

            img = self.webapihelper.clothes_op(img_ori, 'hot underware,', 60.0).image
            await message.reply_photo(byteBufferOfImage(img, 'JPEG'))

    async def send_disallowed_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Sends the disallowed message to the user.
        """
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=self.disallowed_message,
            disable_web_page_preview=True
        )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handles errors in the telegram-python-bot library.
        """
        logging.error(f'Exception while handling an update: {context.error}')

    def is_group_chat(self, update: Update) -> bool:
        """
        Checks if the message was sent from a group chat
        """
        return update.effective_chat.type in [
            constants.ChatType.GROUP,
            constants.ChatType.SUPERGROUP
        ]

    async def is_user_in_group(self, update: Update, context: CallbackContext, user_id: int) -> bool:
        """
        Checks if user_id is a member of the group
        """
        try:
            chat_member = await context.bot.get_chat_member(update.message.chat_id, user_id)
            return chat_member.status in [ChatMember.OWNER, ChatMember.ADMINISTRATOR, ChatMember.MEMBER]
        except telegram.error.BadRequest as e:
            if str(e) == "User not found":
                return False
            else:
                raise e
        except Exception as e:
            raise e

    async def is_allowed(self, update: Update, context: CallbackContext) -> bool:
        """
        Checks if the user is allowed to use the bot.
        """
        if self.config['allowed_user_ids'] == '*':
            return True
        
        if self.is_admin(update):
            return True
        
        allowed_user_ids = self.config['allowed_user_ids'].split(',')
        # Check if user is allowed
        if str(update.message.from_user.id) in allowed_user_ids:
            return True

        # Check if it's a group a chat with at least one authorized member
        if self.is_group_chat(update):
            admin_user_ids = self.config['admin_user_ids'].split(',')
            for user in itertools.chain(allowed_user_ids, admin_user_ids):
                if not user.strip():
                    continue
                if await self.is_user_in_group(update, context, user):
                    logging.info(f'{user} is a member. Allowing group chat message...')
                    return True
            logging.info(f'Group chat messages from user {update.message.from_user.name} '
                f'(id: {update.message.from_user.id}) are not allowed')

        return False

    def is_admin(self, update: Update) -> bool:
        """
        Checks if the user is the admin of the bot.
        The first user in the user list is the admin.
        """
        if self.config['admin_user_ids'] == '-':
            logging.info('No admin user defined.')
            return False

        admin_user_ids = self.config['admin_user_ids'].split(',')

        # Check if user is in the admin user list
        if str(update.message.from_user.id) in admin_user_ids:
            return True

        return False

    def get_reply_to_message_id(self, update: Update):
        """
        Returns the message id of the message to reply to
        :param update: Telegram update object
        :return: Message id of the message to reply to, or None if quoting is disabled
        """
        if self.config['enable_quoting'] or self.is_group_chat(update):
            return update.message.message_id
        return None

    async def post_init(self, application: Application) -> None:
        """
        Post initialization hook for the bot.
        """
        await application.bot.set_my_commands(self.group_commands, scope=BotCommandScopeAllGroupChats())
        await application.bot.set_my_commands(self.commands)

    def run(self):
        """
        Runs the bot indefinitely until the user presses Ctrl+C
        """
        application = ApplicationBuilder() \
            .token(self.config['token']) \
            .proxy_url(self.config['proxy']) \
            .get_updates_proxy_url(self.config['proxy']) \
            .post_init(self.post_init) \
            .concurrent_updates(True) \
            .build()

        application.add_handler(CommandHandler('draw', self.draw))
        application.add_handler(CommandHandler('help', self.help))
        application.add_handler(CommandHandler('model', self.show_model))
        application.add_handler(CommandHandler('start', self.help))

        application.add_handler(CallbackQueryHandler(callback=self.set_model, pattern='GuoFeng|chill|uber'))
        # application.add_handler(CallbackQueryHandler(callback=self.checkpoints))
        application.add_handler(CallbackQueryHandler(callback=self.draw_dress, pattern='.*dress|.*suit|.*wear|.*uniform|armor|hot|bikini|see|.*hanfu'))
        # application.add_handler(CallbackQueryHandler(callback=self.clothes))
        application.add_handler(CallbackQueryHandler(callback=self.draw_bg, pattern='.*beach|grass|space|street|mountain'))


        application.add_handler(MessageHandler(filters.PHOTO & ~filters.Caption('dress|bg'), self.trip))
        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('dress'), self.show_dress))
        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('bg'), self.show_bg))

        #application.add_error_handler(self.error_handler)

        application.run_polling()
