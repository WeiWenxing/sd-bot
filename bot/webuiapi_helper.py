import logging
import webuiapi
from PIL import Image, PngImagePlugin
from io import BytesIO
import numpy as np

def byteBufferOfImage(img, mode):
    img_buffer = BytesIO()
    img.save(img_buffer, mode)
    img_buffer.seek(0)
    return img_buffer

def saveImage(image: Image, fileName):
    image.save(f'{fileName}.jpg', 'JPEG', quality=90)
    return f'{fileName}.jpg'

class WebUIApiHelper:
    """
    WebUI helper class.
    """

    def __init__(self, config: dict):
        """
        Initializes the OpenAI helper class with the given configuration.
        :param config: A dictionary containing the GPT configuration
        """
        self.config = config
        self.cache_image = None
        self.api = webuiapi.WebUIApi(host=config['host'], port=config['port'], use_https=config['use_https'], sampler='DPM++ SDE Karras', steps=15)
        self.prompt_negative = r'(worst quality:2), (low quality:2), (normal quality:2), lowres, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, tattoo, body painting, age spot, (ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), deformed eyes, deformed lips, mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), three arms, extra limbs, extra legs, extra arms, extra hands, (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, pubic hair, glans, easynegative, three feet, four feet, (bra:1.3), (saggy breasts:1.3)'
        # self.prompt_negative = r'easynegative,verybadimagenegative_v1.3,paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans, extra fingers, fewer fingers, Big breasts,huge breasts.bad_hand,wierd_hand,malformed_hand,malformed_finger,paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, skin blemishes, age spot, glans,extra fingers,fewer fingers,long neck, oil paintings,((eye shadow)),bad_posture,wierd_posture,poorly Rendered face,poorly drawn face,poor facial details,poorly drawn ,hands,poorly,rendered hands,low resolution,Images cut out at the top, left, right, bottom.,,bad composition,mutated body parts,blurry image,disfigured,oversaturated,bad anatomy,deformed body features'

    def rep_op(self, photo, area, replace, precision, batch_size, denoising_strength):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]{area}[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, extremely delicate facial, {replace},an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_size, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def clothes_op(self, photo, clothes, alpha):
        #prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0 sketch_color="pink" sketch_alpha={alpha}]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (pink strapless dress:1.6), (see-through:1.6), nude, smooth fair skin, bare shoulders, bare arms, clavicle, large breasts, cleavage, slim waist, bare waist, bare legs, very short hair,leotard, an extremely delicate and beautiful, extremely detailed,intricate,'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, ({clothes}:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_op(self, photo):
        prompt_positive = f'[txt2mask mode="add" show precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth shiny skin, little nipples, bare shoulders, bare arms, bare neck, bare chest, clavicle, large breasts, slim waist, bare waist, bare legs, very short hair,an extremely delicate and beautiful, extremely detailed,intricate,'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=0.0 neg_smoothing=20.0]dress|bra|underwear|skirt|shorts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, small nipples, clavicle, cleavage, large breasts, slim waist, very short hair,an extremely delicate and beautiful, extremely detailed,intricate,<lora:breastinclassBetter_v141:1>'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, <lora:breastinclassBetter_v141:0.6>'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'
        # prompt_positive = r'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask](full body shot topless facing camera),NSFW,((nude)),masterpiece,best quality,delicate ,finely detailed,intricate details,(photorealistic:1.4),naked,k-pop,best quality,ultra high res, (photorealistic:1.4),tits,pink_tits,shinning,4k, high-res,best quality,Korean K-pop idol,vulva,(white_colorful_tatoo),angel_halo,detailed skin texture,<lora:breastinclassBetter_v14:0.4>,(ulzzang-6500-v1.1:0.8),ultra detailed, hiqcgbody, lustrous skin,flat chest, (small breast:1),skinny body, white skin, ((erotic, sexy, horny)) ultra high resolution, highly detailed CG unified 8K wallpapers, physics-based rendering, cinematic lighting, ((good anatomy:1.2)),detailed areolas, detailed nipples, detailed breasts, (extremely detailed pussy),(smooth arms:1.2), (clean arms:1.2), (smallbreast:1),realistic drawing of cute (girl), (full body portrait), (solo focus:1.2), partial nudity, nude belly, laying in bed, (wrapped in white bed blanket:1.3), blush, brown hair, brown eyes, masterpiece, highres, by Jeremy Lipking, by Antonio J Manzanedo, (by Alphonse Mucha:0.5)'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def bg_op(self, photo, bg):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=10.0 smoothing=20.0 negative_mask="face|body|dress|arms|legs|hair" neg_precision=100.0 neg_padding=-4.0 neg_smoothing=20.0]background|scene[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, ({bg}:1.4), very short hair, an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_upper_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face|legs|arms" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|clothes[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def nude_lower_op(self, photo):
        prompt_positive = f'[txt2mask mode="add" show precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]skirts|shorts|underpants|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_repair_op(self, photo, precision, denoising_strength):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def breast_repair_op(self, photo, precision, padding, denoising_strength, batch_count, breast="large breasts,"):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding={padding} smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]breasts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, (absolutely nude:1.6), naked breasts, {breast} perfect breasts, smooth fair skin, procelain skin, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastinclassBetter_v141:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def hand_repair_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]hands[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, extremely delicate facial, normal hands, normal fingers, smooth fair skin, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def lace_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face|legs|arms" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|coat[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (lace bra:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def ext_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = r'(8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, clavicle, large breasts, cleavage, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'

        photo = self.get_ext_image(photo)
        mask = self.get_mask(photo, precision)
        mask = self.get_ext_mask(mask)
        result = self.api.img2img(images=[photo], mask_image=mask, prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def get_mask(self, photo, precision):
        prompt_positive = f'[txt2mask mode="add" show precision={precision} padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask]'
        result = self.api.img2img(images=[photo], prompt=prompt_positive, cfg_scale=7, batch_size=1, denoising_strength=0.0, inpainting_fill=0, steps=1)
        mask = None
        for image in result.images:
            if image.mode == "RGBA":
                mask = image
        return mask

    def get_ext_mask(self, mask):
        # 将PIL Image对象转换为NumPy数组
        mask_array = np.array(mask)

        # 获取数组的高度和宽度
        height, width = mask_array.shape[:2]

        # 计算需要涂白的区域
        y_start = int(height * 0.6)
        mask_array[y_start:, :, :] = 255

        # 将NumPy数组转换为PIL Image对象
        mask_white = Image.fromarray(mask_array)

        # 返回更新后的蒙版Image对象
        return mask_white


    def get_ext_image(self, image):
        w, h = image.size
        logging.info
        nw = int(w*0.6)
        nh = int(h*0.6)
        image = image.resize((nw, nh), Image.BICUBIC)

        img_array = np.array(image)
        height, width, channels = img_array.shape
        new_array = np.zeros((h, width, channels), dtype=np.uint8)

        new_array[:height, :, :] = img_array

        # 获取原始图像下边缘的颜色
        bottom_colors = img_array[height-1, :, :]
        # 对新数组下边缘的像素进行填充
        new_array[height:h, :, :] = np.tile(bottom_colors, (h - height, 1)).reshape((h - height, width, channels))

        # bottom_color = (229, 205, 197)  # 将 R, G, B 替换成你想要的颜色值
        # bottom_colors = np.full((h - height, width, channels), bottom_color, dtype=np.uint8)
        # new_array[height:h, :, :] = bottom_colors

        # 将 numpy 数组转换为 PIL Image 对象
        new_image = Image.fromarray(new_array)
        return new_image
