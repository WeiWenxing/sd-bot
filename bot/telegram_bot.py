import logging
import itertools
import datetime
from PIL import Image, PngImagePlugin, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO
import torch

import telegram
from telegram import constants, BotCommandScopeAllGroupChats
from telegram import Message, MessageEntity, Update, \
    BotCommand, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, \
    filters, InlineQueryHandler, Application, CallbackContext, CallbackQueryHandler

from webuiapi_helper import WebUIApiHelper, byteBufferOfImage, saveImage
from config import telegram_config
from queueinfo import QueueInfo

WATERMARK = r'fake pic by @aipicfree'


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


def add_txt_to_img(image: Image, txt, font_size=60, angle=0, color=(128, 128, 128), alpha=0.2) -> Image:
    w, h = image.size
    # text_pic = Image.new('RGBA', (4 * h, 4 * w), (255, 255, 255, 255))
    text_pic = Image.new('RGBA', (h, w), (255, 255, 255, 255))

    fnt = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf", font_size)

    text_d = ImageDraw.Draw(text_pic)

    # a, b 分别控制水印的列间距和行间距，默认为字体的2倍列距，4倍行距

    # a, b = 1, 6
    # for x in range(10, text_pic.size[0] - 10, a * font_size * len(txt)):
    #     for y in range(10, text_pic.size[1] - 10, b * font_size):
    #         text_d.multiline_text((x, y), txt, fill=color, font=fnt)

    text_d.text((40, 10), txt, fill=color, font=fnt)
    # text_d.text((40, h - 6*font_size), txt, fill=color, font=fnt)

    # 旋转水印
    text_pic = text_pic.rotate(angle)
    # 截取水印部分图片
    # text_pic = text_pic.crop((h, w, 3 * h, 3 * w))
    text_pic = text_pic.resize(image.size)
    text_pic = text_pic.convert('RGB')
    logging.info(f"text_pic: {text_pic.size}, image: {image.size}")
    result = Image.blend(image, text_pic, alpha)
    result = result.convert('RGB')
    enhance = ImageEnhance.Contrast(result)
    result = enhance.enhance(1.0 / (1 - alpha))
    return result

class SDBot:
    """
    Class representing a ChatGPT Telegram Bot.
    """

    def __init__(self, api: WebUIApiHelper):
        """
        Initializes the bot with the given configuration and GPT bot object.
        :param config: A dictionary containing the bot configuration
        :param api: WebUIApiHelper object
        """
        self.config = telegram_config
        self.webapihelper = api
        self.commands = [
            BotCommand(command='help', description='Show help message'),
        ]
        self.group_commands = [
            BotCommand(command='chat', description='Chat with the bot!')
        ] + self.commands
        self.disallowed_message = "Sorry, you are not allowed to use this bot. You can connect to @aisexypic"
        self.budget_limit_message = "Sorry, you have reached your monthly usage limit."
        self.usage = {}
        self.last_message = {}
        self.photo_commands = [
            BotCommand(command='dress', description='send me a photo with caption "dress", you can change clothes'),
        ]
        self.queue_max = 5
        self.queue = QueueInfo()

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Shows the help menu.
        """
        commands = self.group_commands if self.is_group_chat(update) else self.commands
        commands.extend(self.photo_commands)
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

        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            image_query = message_text(message)
            if image_query == '':
                await message.reply_text('Please provide a prompt! (e.g. /draw cat)')
                return

            logging.info(f'New image generation request received from user {update.message.from_user.name}')
            result = self.webapihelper.txt2img_op(image_query)
            await message.reply_photo(byteBufferOfImage(result.image, 'JPEG'))

    async def show_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        keyboard = [
            [
                InlineKeyboardButton("majic", callback_data="majicmixRealistic_v4.inpainting"),
                InlineKeyboardButton("GF3.2", callback_data="GuoFeng3.2"),
                InlineKeyboardButton("mix", callback_data="majicmixRealistic_v4"),
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
                InlineKeyboardButton("情趣", callback_data="crotchless,"),
                InlineKeyboardButton("内衣", callback_data="hot underware,"),
                InlineKeyboardButton("制服", callback_data="police_uniform,"),
                InlineKeyboardButton("学院", callback_data="school_uniform,"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        self.webapihelper.cache_image = await self.get_img_from_msg(context.bot, update.message)
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
            result = self.webapihelper.clothes_op(self.webapihelper.cache_image, clothes)
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
        self.webapihelper.cache_image = await self.get_img_from_msg(context.bot, update.message)
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

    async def get_img_from_msg(self, bot, message):
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

        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo and len(message.photo) == 1:
                img_ori = await self.down_image(bot, message)
                # img = add_txt_to_img(img_ori, WATERMARK)
                # await message.reply_photo(byteBufferOfImage(img, 'JPEG'))
                # return

                # logging.info(f"=============================nude upper===============================")
                # img = self.webapihelper.nude_upper_op(img).image
                # await message.reply_photo(byteBufferOfImage(img, 'JPEG'))

                # logging.info(f"=============================nude lower===============================")
                # result = self.webapihelper.nude_lower_op(img)
                # for image in result.images:
                #     type_mode = 'PNG' if image.mode == "RGBA" else 'JPEG'
                #     await message.reply_photo(byteBufferOfImage(image, type_mode))

                # logging.info(f"=============================nude repair===============================")
                # img = self.webapihelper.nude_repair_op(img, 70.0, 0.45).image
                # await message.reply_photo(byteBufferOfImage(img, 'JPEG'))

                logging.info(f"=============================nude1 full===============================")
                result = self.webapihelper.nude1_op(img_ori)
                for image in result.images:
                    type_mode = 'PNG' if image.mode == "RGBA" else 'JPEG'
                    # image = image if image.mode == "RGBA" else add_txt_to_img(image, WATERMARK)
                    await message.reply_photo(byteBufferOfImage(image, type_mode))

                # img = result.image
                # logging.info(f"=============================repair breasts===============================")
                # result = self.webapihelper.breast_repair_op(img, precision=100, padding=4.0, denoising_strength=0.7, batch_count=1)
                # for image in result.images:
                #     type_mode = 'PNG' if image.mode == "RGBA" else 'JPEG'
                #     # image = image if image.mode == "RGBA" else add_txt_to_img(image, WATERMARK)
                #     await message.reply_photo(byteBufferOfImage(image, type_mode))

                logging.info(f"=============================underwear===============================")
                image = self.webapihelper.clothes_op(img_ori, 'hot underwear,').image
                # image = add_txt_to_img(image, WATERMARK)
                await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

                logging.info(f"=============================nude full===============================")
                result = self.webapihelper.nude_op(img_ori)
                for image in result.images:
                    type_mode = 'PNG' if image.mode == "RGBA" else 'JPEG'
                    # image = image if image.mode == "RGBA" else add_txt_to_img(image, WATERMARK)
                    await message.reply_photo(byteBufferOfImage(image, type_mode))

                # img = result.image
                # logging.info(f"=============================repair breasts===============================")
                # result = self.webapihelper.breast_repair_op(img, precision=100, padding=4.0, denoising_strength=0.7, batch_count=1)
                # for image in result.images:
                #     type_mode = 'PNG' if image.mode == "RGBA" else 'JPEG'
                #     # image = image if image.mode == "RGBA" else add_txt_to_img(image, WATERMARK)
                #     await message.reply_photo(byteBufferOfImage(image, type_mode))

                logging.info(f"=============================all full===============================")
                result = self.webapihelper.nude_repair_op(img_ori, precision=65, denoising_strength=1.0, batch_size=1)
                for image in result.images:
                    type_mode = 'PNG' if image.mode == "RGBA" else 'JPEG'
                    # image = image if image.mode == "RGBA" else add_txt_to_img(image, WATERMARK)
                    await message.reply_photo(byteBufferOfImage(image, type_mode))
            else:
                await message.reply_text(f'please send one photo!')

    async def repair_breasts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return

        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================repair breasts===============================")
                # result = self.webapihelper.breast_repair_op(img, precision=100, padding=4.0, denoising_strength=0.7, batch_count=2)
                # for image in result.images:
                #     await message.reply_photo(byteBufferOfImage(image, 'JPEG'))
                result = self.webapihelper.breast_repair_op(img, precision=85, padding=4.0, denoising_strength=0.7, batch_count=4)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def repair_hand(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================repair hand===============================")
                result = self.webapihelper.hand_repair_op(img, 100, 0.7, 2)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def lace(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================lace===============================")
                result = self.webapihelper.lace_op(img, 100, 1, 4)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def crotch(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                logging.info(f"=============================crotchless===============================")
                result = self.webapihelper.clothes_op(img_ori, 'crotchless,', batch_size=4)

                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def upper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================upper nude===============================")
                result = self.webapihelper.nude_upper_op(img, 100, 1, 2)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))
                    # image = self.webapihelper.breast_repair_op(image, precision=100, padding=-4.0, denoising_strength=0.7, batch_count=1).image
                    # await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def lower(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================lower nude===============================")
                result = self.webapihelper.nude_lower_op(img, 100, 1, 2)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def ext(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================ext===============================")
                result = self.webapihelper.get_ext_image(img)
                await message.reply_photo(byteBufferOfImage(result, 'JPEG'))

                result = self.webapihelper.ext_ori_op(result, 1, 2)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def rep(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            logging.info(message.caption)
            strs = message.caption.split()
            logging.info(strs)
            if len(strs) < 3:
                await message.reply_text(r'please input more than 2 words')
                return

            area = strs[1]
            replacement = " ".join(strs[2:])
            logging.info(replacement)

            bot = context.bot
            if message.photo:
                img_ori = await self.down_image(bot, message)

                img = img_ori
                logging.info(f"=============================rep===============================")
                result = self.webapihelper.rep_op(photo=img, area=area, replace=replacement, precision=100.0, batch_size=4, denoising_strength=1)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def clip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img = await self.down_image(bot, message, enhance_face=False)
                result = self.webapihelper.clip_seg(img, "dress|skirt|underwear", "face|arms")
                await message.reply_photo(byteBufferOfImage(result, 'PNG'))

    async def all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                img = await self.down_image(bot, message, enhance_face=False)
                result = self.webapihelper.nude_repair_op(img, precision=65, denoising_strength=0.8, batch_size=4)
                for image in result.images:
                    await message.reply_photo(byteBufferOfImage(image, 'JPEG'))

    async def png_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            logging.info(message)
            if message.document:
                img = await self.down_image(bot, message, enhance_face=False, is_doc=True)
                result = self.webapihelper.info_op(img)
                logging.info(result)
                await message.reply_text(f'{result.info}\n{result.parameters}')

    async def high(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_allowed(update, context):
            logging.warning(f'User {update.message.from_user.name}: {update.message.from_user.id} is not allowed to use this bot')
            await self.send_disallowed_message(update, context)
            return
        logging.info(f'queue is: {self.queue.size}')
        if 0 < self.queue_max < self.queue.size:
            logging.info("queue is full, please wait for a minute and retry！")
            await update.message.reply_text('queue is full, please wait for a minute and retry！')
            return

        K = await update.message.reply_text(f"In line, there are {self.queue.size} people ahead")
        async with self.queue:
            await K.delete()
            message = update.message
            bot = context.bot
            if message.photo:
                # path = await self.down_image_to_path(bot, message)
                # img = self.open_image_from_path(path)
                img = await self.down_image(bot, message, enhance_face=False)
                logging.info(f"=============================high resolution===============================")

                result = self.webapihelper.high1_op(img, upscaling_resize=2)

                torch.cuda.empty_cache()
                logging.info(result.image.size)
                await message.reply_photo(byteBufferOfImage(result.image, 'JPEG'))

                date = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')
                path = f'download/high_{date}'
                high_pic = saveImage(result.image, path, quality=90)
                logging.info(high_pic)
                await message.reply_document(high_pic)

    async def down_image(self, bot, message, enhance_face=False, is_doc=False):
        logging.info("Message contains one photo.")
        if not is_doc:
            file = await bot.getFile(message.photo[-1].file_id)
        else:
            file = await bot.getFile(message.document.file_id)
        logging.info(file)
        bytes = await file.download_as_bytearray()
        image = Image.open(BytesIO(bytes))

        if enhance_face:
            image = await self.upscale_face(bot, message, image)

        return image

    async def upscale_face(self, bot, message, image):
        result = self.webapihelper.high_op(image, upscaling_resize=1)
        face_message = await message.reply_photo(byteBufferOfImage(result.image, 'JPEG'))
        file = await bot.getFile(face_message.photo[-1].file_id)
        logging.info(file)
        bytes = await file.download_as_bytearray()
        image = Image.open(BytesIO(bytes))
        return image

    async def down_image_to_path(self, bot, message):
        logging.info("Message contains one photo.")
        date = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')
        path = f'download/photo_{date}.jpg'
        logging.info(f"{path}")
        file = await bot.getFile(message.photo[-1].file_id)
        logging.info(file)
        photo_path = await file.download_to_drive(custom_path=path)
        logging.info(photo_path)
        return str(photo_path)

    def open_image_from_path(self, photo_path):
        logging.info(photo_path)
        with open(photo_path, "rb") as f:
            file_bytes = f.read()
        img_ori = Image.open(BytesIO(file_bytes))
        return img_ori

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
            logging.info(f'user_name: {update.message.from_user.name}, user_id: {update.message.from_user.id} is allowed!! user_lang: {update.message.from_user.language_code}')
            return True
        
        allowed_user_ids = self.config['allowed_user_ids'].split(',')
        # Check if user is allowed
        if str(update.message.from_user.id) in allowed_user_ids:
            logging.info(f'user_name: {update.message.from_user.name}, user_id: {update.message.from_user.id} is allowed!! user_lang: {update.message.from_user.language_code}')
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

        if str(update.message.from_user.language_code).startswith('zh'):
            self.disallowed_message = "Sorry, you are not allowed to use this bot. You can connect to @aipicfree"
        else:
            self.disallowed_message = "Sorry, you are not allowed to use this bot. You can connect to @aisexypic"
        logging.info(f'user_name: {update.message.from_user.name}, user_id: {update.message.from_user.id} is not allowed!! user_lang: {update.message.from_user.language_code}')
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

    async def run(self):
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

        application.add_handler(CallbackQueryHandler(callback=self.set_model, pattern='GuoFeng|chill|uber|majic'))
        # application.add_handler(CallbackQueryHandler(callback=self.checkpoints))
        application.add_handler(CallbackQueryHandler(callback=self.draw_dress, pattern='.*dress|.*suit|.*wear|.*uniform|crotchless|armor|hot|bikini|see|.*hanfu'))
        # application.add_handler(CallbackQueryHandler(callback=self.clothes))
        application.add_handler(CallbackQueryHandler(callback=self.draw_bg, pattern='.*beach|grass|space|street|mountain'))

        application.add_handler(MessageHandler(filters.PHOTO & ~filters.Caption('dress|bg|mi|hand|ll|cc|up|lower|ext|rep|hi|clip|all'), self.trip))
        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('dress'), self.show_dress))
        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('bg'), self.show_bg))
        self.photo_commands.append(BotCommand('bg', 'send me a photo with caption "bg" to change background.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('mi'), self.repair_breasts))
        self.photo_commands.append(BotCommand('mi', 'send me a photo with caption "mi" to repair breasts and nipples.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('hand'), self.repair_hand))
        self.photo_commands.append(BotCommand('hand', 'send me a photo with caption "bg" to repair hands.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('ll'), self.lace))
        self.photo_commands.append(BotCommand('ll', 'send me a photo with caption "ll" to change clothes to lace bra.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('cc'), self.crotch))
        self.photo_commands.append(BotCommand('cc', 'send me a photo with caption "cc" to change clothes to hot underwear.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('up'), self.upper))
        self.photo_commands.append(BotCommand('up', 'send me a photo with caption "up" to nude upper body.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('lower'), self.lower))
        self.photo_commands.append(BotCommand('lower', 'send me a photo with caption "lower" to nude lower body.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('ext'), self.ext))
        self.photo_commands.append(BotCommand('ext', 'send me a photo with caption "ext" to out painting picture.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('rep'), self.rep))
        self.photo_commands.append(BotCommand('rep', 'send me a photo with caption "rep <place> <what>" to replace area to something.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('hi'), self.high))
        self.photo_commands.append(BotCommand('hi', 'send me a photo with caption "hi" to high resolution for picture.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('clip'), self.clip))
        # self.photo_commands.append(BotCommand('clip', 'send me a photo with caption "clip" to change clothes to lace bra.'))

        application.add_handler(MessageHandler(filters.PHOTO & filters.Caption('all'), self.all))
        self.photo_commands.append(BotCommand('all', 'send me a photo with caption "all" to nude 1girl all except face.'))

        application.add_handler(MessageHandler(filters.Document.IMAGE, self.png_info))

        # application.add_handler(MessageHandler(filters.PHOTO & filters.CaptionRegex('all'), self.all))

        #application.add_error_handler(self.error_handler)

        # application.run_polling()
        await application.initialize()
        await application.start()
        logging.info("启动完毕，接收消息中……")
        await application.updater.start_polling(drop_pending_updates=True)

    async def start_task(self):
        """|coro|
        以异步方式启动
        """
        return await self.run()