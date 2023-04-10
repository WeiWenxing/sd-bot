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
        self.api = webuiapi.WebUIApi(host=config['host'], port=config['port'], use_https=config['use_https'], sampler='DPM++ SDE Karras', steps=10)
        self.prompt_negative = r'(worst quality:2), (low quality:2), (normal quality:2), lowres, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, tattoo, body painting, age spot, (ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), deformed eyes, deformed lips, mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), three arms, extra limbs, extra legs, extra arms, extra hands, (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, pubic hair, glans, easynegative, three feet, four feet, (bra:1.3)'

    def clothes_op(self, photo, color, alpha):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0 sketch_color="{color}" sketch_alpha={alpha}]dress|bra|underwear[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, ({color} strapless dress:1.6), (see-through:1.6), nude, smooth fair skin, bare shoulders, bare arms, clavicle, large breasts, cleavage, slim waist, bare waist, bare legs, very short hair,leotard, an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.debug(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=0.45, inpainting_fill=1)
        return result

    def nude_op(self, photo, color, alpha):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0 sketch_color="{color}" sketch_alpha={alpha}]dress|bra|underwear[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, little nipples, bare shoulders, bare arms, bare neck, bare chest, clavicle, naked large breasts, slim waist, bare waist, bare legs, very short hair,an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.debug(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=0.45, inpainting_fill=1)
        return result