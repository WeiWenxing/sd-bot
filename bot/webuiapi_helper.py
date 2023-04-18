import logging
import webuiapi
from PIL import Image, PngImagePlugin
from io import BytesIO

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
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def bg_op(self, photo, bg):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=10.0 smoothing=20.0 negative_mask="face|body|dress|arms|legs|hair" neg_precision=100.0 neg_padding=-4.0 neg_smoothing=20.0]background|scene[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, ({bg}:1.4), very short hair, an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_upper_op(self, photo):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face|legs" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|clothes[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_lower_op(self, photo):
        prompt_positive = f'[txt2mask mode="add" show precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]skirts|shorts|underpants|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, slim waist, an extremely delicate and beautiful, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_repair_op(self, photo, precision, denoising_strength):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def nude_breast_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]breasts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def breast_repair_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]breasts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, large breasts, perfect breasts, smooth fair skin, procelain skin, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def hand_repair_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]hands[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, extremely delicate facial, normal hands, normal fingers, smooth fair skin, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result