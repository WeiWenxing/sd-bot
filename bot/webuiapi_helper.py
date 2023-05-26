import logging
import webuiapi
from PIL import Image, PngImagePlugin
from io import BytesIO
import numpy as np
#import mask_clipseg


def byteBufferOfImage(img, mode):
    img_buffer = BytesIO()
    img.save(img_buffer, mode)
    img_buffer.seek(0)
    return img_buffer


def saveImage(image: Image, fileName, quality=100):
    image.save(f'{fileName}.jpg', 'JPEG', quality=quality)
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
        self.prompt_negative = r'ng_deepnegative_v1_75t, (worst quality:2), (low quality:2), (normal quality:2), lowres, ((monochrome)), ((grayscale)), easynegative, badhandsv5, skin spots, acnes, skin blemishes, tattoo, body painting, age spot, (ugly:1.331), (duplicate:1.331), (morbid:1.21), (mutilated:1.21), (tranny:1.331), deformed eyes, deformed lips, mutated hands, (poorly drawn hands:1.331), blurry, (bad anatomy:1.21), (bad proportions:1.331), three arms, extra limbs, extra legs, extra arms, extra hands, (more than 2 nipples:1.331), (missing arms:1.331), (extra legs:1.331), (fused fingers:1.61051), (too many fingers:1.61051), (unclear eyes:1.331), bad hands, missing fingers, extra digit, (futa:1.1), bad body, pubic hair, glans, easynegative, three feet, four feet, (bra:1.3), (saggy breasts:1.3)'
        # self.prompt_negative = r'easynegative,verybadimagenegative_v1.3,paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, acnes, skin blemishes, age spot, glans, extra fingers, fewer fingers, Big breasts,huge breasts.bad_hand,wierd_hand,malformed_hand,malformed_finger,paintings, sketches, (worst quality:2), (low quality:2), (normal quality:2), lowres, normal quality, ((monochrome)), ((grayscale)), skin spots, skin blemishes, age spot, glans,extra fingers,fewer fingers,long neck, oil paintings,((eye shadow)),bad_posture,wierd_posture,poorly Rendered face,poorly drawn face,poor facial details,poorly drawn ,hands,poorly,rendered hands,low resolution,Images cut out at the top, left, right, bottom.,,bad composition,mutated body parts,blurry image,disfigured,oversaturated,bad anatomy,deformed body features'
        # args see:  https://github.com/pkuliyi2015/multidiffusion-upscaler-for-automatic1111/blob/main/scripts/tilediffusion.py
        self.alwayson_scripts_tiled_vae = {
            'Tiled VAE': {
                "args": [True, True, True, True, False, 1024, 128],
            },
        }
        self.alwayson_scripts = {
            "Tiled Diffusion": {
                "args": [
                    True,
                    "MultiDiffusion",
                    True,
                    10,
                    1,
                    1,
                    64,
                    True,
                    True,
                    512,
                    512,
                    96,
                    96,
                    48,
                    1,
                    "R-ESRGAN 4x+",
                    1.5,
                    False,
                    False,
                    False,
                    False,
                    None,
                ],
            },
            'Tiled VAE': {
                "args": [True, True, True, True, False, 1024, 128],
            },
        }

    def rep_op(self, photo, area, replace, precision, batch_size, denoising_strength):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]{area}[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, extremely delicate facial, {replace},an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_size, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def clothes_op(self, photo, clothes, batch_size=1):
        #prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0 sketch_color="pink" sketch_alpha={alpha}]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (pink strapless dress:1.6), (see-through:1.6), nude, smooth fair skin, bare shoulders, bare arms, clavicle, large breasts, cleavage, slim waist, bare waist, bare legs, very short hair,leotard, an extremely delicate and beautiful, extremely detailed,intricate,'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face|mask" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, ({clothes}:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_size, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_op(self, photo):
        prompt_positive = f'[txt2mask mode="add" show precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth shiny skin, little nipples, bare shoulders, bare arms, bare neck, bare chest, clavicle, large breasts, slim waist, bare waist, bare legs, very short hair,an extremely delicate and beautiful, extremely detailed,intricate,'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=0.0 neg_smoothing=20.0]dress|bra|underwear|skirt|shorts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, small nipples, clavicle, cleavage, large breasts, slim waist, very short hair,an extremely delicate and beautiful, extremely detailed,intricate,<lora:breastinclassBetter_v141:1>'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, <lora:breastinclassBetter_v141:0.6>'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face|mask" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|vest|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'
        # prompt_positive = r'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask](full body shot topless facing camera),NSFW,((nude)),masterpiece,best quality,delicate ,finely detailed,intricate details,(photorealistic:1.4),naked,k-pop,best quality,ultra high res, (photorealistic:1.4),tits,pink_tits,shinning,4k, high-res,best quality,Korean K-pop idol,vulva,(white_colorful_tatoo),angel_halo,detailed skin texture,<lora:breastinclassBetter_v14:0.4>,(ulzzang-6500-v1.1:0.8),ultra detailed, hiqcgbody, lustrous skin,flat chest, (small breast:1),skinny body, white skin, ((erotic, sexy, horny)) ultra high resolution, highly detailed CG unified 8K wallpapers, physics-based rendering, cinematic lighting, ((good anatomy:1.2)),detailed areolas, detailed nipples, detailed breasts, (extremely detailed pussy),(smooth arms:1.2), (clean arms:1.2), (smallbreast:1),realistic drawing of cute (girl), (full body portrait), (solo focus:1.2), partial nudity, nude belly, laying in bed, (wrapped in white bed blanket:1.3), blush, brown hair, brown eyes, masterpiece, highres, by Jeremy Lipking, by Antonio J Manzanedo, (by Alphonse Mucha:0.5)'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude1_op(self, photo):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="face|mask|arms|hands" neg_precision=100.0 neg_padding=0.0 neg_smoothing=20.0]dress|clothes|bra|vest|underwear|skirts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, arms in back, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'
        logging.info(f'prompt_positive: {prompt_positive}')
        # result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10, alwayson_scripts=self.alwayson_scripts_tiled_vae)
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def skin_op(self, photo, color="229,205,197", alpha=80.0):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=4.0 smoothing=20.0 negative_mask="face|mask|head|hair" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0 sketch_color={color} sketch_alpha={alpha}]person|dress|clothes|bra|vest|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=4, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def bg_op(self, photo, bg):
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=10.0 smoothing=20.0 negative_mask="face|body|dress|arms|legs|hair" neg_precision=100.0 neg_padding=2.0 neg_smoothing=10.0]background|scene[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, ({bg}:1.4), very short hair, an extremely delicate and beautiful, extremely detailed,intricate,'
        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=1, denoising_strength=1, inpainting_fill=1, steps=10)
        return result

    def nude_upper_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face|legs|arms" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|clothes|skirts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def nude_lower_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" show precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]skirts|shorts|underpants|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, slim waist, spread legs, spread_pussy, open vagina, stretched vagina, puffy pussy, cum inside vagina pouring, an extremely delicate and beautiful, extremely detailed,intricate, <lora:newb_0.1:0.3>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def pussy_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" show precision={precision} padding=4.0 smoothing=20.0  negative_mask="face|mask" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]pussy|skirts|shorts|underpants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, (absolutely nude:1.6), spread_pussy, open vagina, stretched vagina, cum inside vagina pouring, an extremely delicate and beautiful, extremely detailed,intricate,'
        prompt_positive = f'[txt2mask mode="add" precision=100.0 padding=8.0 smoothing=20.0 negative_mask="arms|hands" neg_precision=100.0 neg_padding=0.0 neg_smoothing=20.0]pixlate|mosaic[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, arms in back, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def depixlate_op(self, photo, precision=100.0, denoising_strength=1.0, batch_count=1):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=8.0 smoothing=20.0  negative_mask="arms|hands" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]pixlate|mosaic[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, arms in back, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10, sampler_name='DPM++ 2M Karras')
        return result

    def nude_repair_op(self, photo, precision, denoising_strength, batch_size):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face|head" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_size, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def cum_op(self, photo, precision, denoising_strength, batch_size):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, (cum on body:1.6), an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_size, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def breast_repair_op(self, photo, precision, padding, denoising_strength, batch_count, breast="large breasts,"):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding={padding} smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]breasts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, (absolutely nude:1.6), naked breasts, {breast} perfect breasts, smooth fair skin, procelain skin, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastinclassBetter_v141:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def breast_repair1_op(self, photo, precision, padding, denoising_strength, batch_count, breast="large breasts,"):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding={padding} smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]breasts[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, (absolutely nude:1.6), naked breasts, {breast} perfect breasts, smooth fair skin, procelain skin, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def hand_repair_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="face" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]hands[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, extremely delicate facial, normal hands, normal fingers, smooth fair skin, extremely detailed,intricate,'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def lace_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=4.0 smoothing=20.0 negative_mask="head|face|legs|arms" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|bra|underwear|coat[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (lace bra:1.6), smooth fair skin, procelain skin,  clavicle, large breasts, cleavage, slim waist, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>'

        logging.info(f'prompt_positive: {prompt_positive}')
        result = self.api.img2img(images=[photo], prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def high_op(self, image, upscaling_resize):
        result = self.api.extra_single_image(image=image, upscaler_1=webuiapi.Upscaler.ESRGAN_4x, gfpgan_visibility=1, upscaling_resize=upscaling_resize)
        return result

    def high1_op(self, image, upscaling_resize=2):
        result = self.api.extra_single_image(image=image, upscaler_1="R-ESRGAN 4x+", gfpgan_visibility=1, upscaling_resize=upscaling_resize)
        # result = self.api.extra_single_image(image=image, upscaler_1="4x-UltraSharp", gfpgan_visibility=1, upscaling_resize=upscaling_resize)
        return result

    def info_op(self, image):
        result = self.api.png_info(image=image)
        return result

    def ext_ori_op(self, ext_photo, denoising_strength=1.0, batch_count=1):
        prompt_positive = f'(8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, standing, arms in back, outdoor, extremely delicate facial, extremely detailed,intricate,'
        logging.info(prompt_positive)
        photo = ext_photo

        mask = self.get_empty_mask(photo)
        mask = self.get_ext_mask(mask, padding=-4)
        result = self.api.img2img(images=[photo], mask_image=mask, prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def ext_op(self, photo, precision, denoising_strength, batch_count):
        prompt_positive = r'(8k, RAW photo, best quality, masterpiece:1.2), (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, clavicle, large breasts, cleavage, slim waist, very short hair, an extremely delicate and beautiful, extremely detailed,intricate, (breasts pressed against glass:1.3), <lora:breastsOnGlass_v10:0.8>,'
        prompt_positive = f'[txt2mask mode="add" precision={precision} padding=8.0 smoothing=20.0 negative_mask="face|head|mask" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask](8k, RAW photo, best quality, masterpiece:1.2), 3d, (realistic, photo-realistic:1.37), fmasterpiecel, 1girl, extremely delicate facial, perfect female figure, (absolutely nude:1.6), smooth fair skin, procelain skin, lustrous skin, clavicle, cleavage, slim waist, very short hair, extremely detailed,intricate, <lora:breastinclassBetter_v141:0.8>,'
        logging.info(prompt_positive)

        photo = self.get_ext_image(photo)
        mask = self.get_empty_mask(photo)
        # mask = self.clip_seg(photo, "dress|clothes|bra|underwear|pants", "face|mask", mask_precision=90, mask_padding=8)  # self.get_empty_mask(photo)
        mask = self.get_ext_mask(mask, padding=6)
        # mask = mask_clipseg.overlay_mask_part(mask, ext_mask, 1)
        result = self.api.img2img(images=[photo], mask_image=mask, prompt=prompt_positive, negative_prompt=self.prompt_negative, cfg_scale=7, batch_size=batch_count, denoising_strength=denoising_strength, inpainting_fill=1, steps=10)
        return result

    def get_mask(self, photo, precision):
        prompt_positive = f'[txt2mask mode="add" show precision={precision} padding=8.0 smoothing=20.0 negative_mask="face|arms|hands" neg_precision=100.0 neg_padding=4.0 neg_smoothing=20.0]dress|clothes|bra|underwear|pants[/txt2mask]nude'
        result = self.api.img2img(images=[photo], prompt=prompt_positive, cfg_scale=7, batch_size=1, denoising_strength=0.0, inpainting_fill=1, steps=1)
        logging.info(result)
        for image in result.images:
            if image.mode == "RGBA":
                return image
        return None
        # return self.get_empty_mask(photo)

    def clip_seg(self, photo, mask_prompt, negative_mask_prompt, mask_precision=100, mask_padding=4):
        logging.info(f'mask_prompt: {mask_prompt}')
        logging.info(f'negative_mask_prompt: {negative_mask_prompt}')
        return photo  # mask_clipseg.run(photo, mask_prompt, negative_mask_prompt, mask_precision=mask_precision, mask_padding=mask_padding)

    def get_ext_mask(self, mask, padding=4):
        # 将PIL Image对象转换为NumPy数组
        mask_array = np.array(mask)

        # 获取数组的高度和宽度
        height, width = mask_array.shape[:2]

        # 计算需要涂白的区域
        y_start = int(height * 0.6)-padding
        left_edge = int(width * 0.2)+padding
        right_edge = int(width * 0.8)-padding
        mask_array[y_start:, :, :] = 255
        mask_array[:y_start, :left_edge, :] = 255
        mask_array[:y_start, right_edge:width, :] = 255

        # 将NumPy数组转换为PIL Image对象
        mask_white = Image.fromarray(mask_array)

        # 返回更新后的蒙版Image对象
        return mask_white

    def get_empty_mask(self, image):
        image_array = np.array(image)
        height, width, channels = image_array.shape
        mask_array = np.zeros((height, width, channels), dtype=np.uint8)
        mask = Image.fromarray(mask_array)
        return mask

    def get_ext_image(self, image, edge=2):
        w, h = image.size
        logging.info
        nw = int(w*0.6)
        nh = int(h*0.6)
        image = image.resize((nw, nh), Image.BICUBIC)

        img_array = np.array(image)
        height, width, channels = img_array.shape
        new_array = np.zeros((h, w, channels), dtype=np.uint8)

        new_array[:height, (w-width)//2:(w-width)//2+width, :] = img_array

        # 获取原图左边缘的颜色
        left_colors = img_array[:, edge, :]
        new_array[:height, :(w-width)//2, :] = np.tile(left_colors, (1, (w-width)//2)).reshape((height, (w-width)//2, channels))

        # 获取原右边缘的颜色
        right_colors = img_array[:, width - edge, :]
        new_array[:height, (w+width)//2:w, :] = np.tile(right_colors, (1, w-(w+width)//2)).reshape((height, w-(w+width)//2, channels))

        # 获取原始图像下边缘的颜色
        bottom_colors = new_array[height-edge, :, :]
        new_array[height:h, :, :] = np.tile(bottom_colors, (h - height, 1)).reshape((h - height, w, channels))

        # color = (128, 128, 128)  # (229, 205, 197)  # 将 R, G, B 替换成你想要的颜色值
        # bottom_colors = np.full((h - height, w, channels), color, dtype=np.uint8)
        # new_array[height:h, :, :] = bottom_colors
        # left_colors = np.full((height, (w-width)//2, channels), color, dtype=np.uint8)
        # new_array[:height, :(w-width)//2, :] = left_colors
        # right_colors = np.full((height, w - (w+width)//2, channels), color, dtype=np.uint8)
        # new_array[:height, (w+width)//2:w, :] = right_colors

        # 将 numpy 数组转换为 PIL Image 对象
        new_image = Image.fromarray(new_array)
        return new_image

    def txt2img_op(self, prompt):
        prompt_neg= r'(worst quality, low quality:1.4), (fuze:1.4), (worst quality:1.1), (low quality:1.4:1.1), lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurrypolar,bad body,bad proportions,gross proportions,text,error,missing fingers, missing arms,missing legs, extra digit, extra fingers,fewer digits,extra limbs,extra arms,extra legs,malformed limbs,fused fingers,too many fingers,long neck,cross-eyed,mutated hands, cropped,poorly drawn hands,poorly drawn face,mutation,deformed,worst quality,low quality, normal quality, blurry,ugly,duplicate,morbid,mutilated,out of frame, body out of frame,'
        result = self.api.txt2img(prompt=prompt, negative_prompt=prompt_neg, width=512, height=768, batch_size=4, denoising_strength=0.45, enable_hr=True, hr_second_pass_steps=10, hr_scale=1.5, restore_faces=True, steps=10, seed=-1, sampler_name='DPM++ 2M Karras', )
        return result

    def out_op(self, prompt):
        prompt_neg= r'(worst quality, low quality:1.4), (fuze:1.4), (worst quality:1.1), (low quality:1.4:1.1), lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurrypolar,bad body,bad proportions,gross proportions,text,error,missing fingers, missing arms,missing legs, extra digit, extra fingers,fewer digits,extra limbs,extra arms,extra legs,malformed limbs,fused fingers,too many fingers,long neck,cross-eyed,mutated hands, cropped,poorly drawn hands,poorly drawn face,mutation,deformed,worst quality,low quality, normal quality, blurry,ugly,duplicate,morbid,mutilated,out of frame, body out of frame,'
        result = self.api.txt2img(prompt=prompt, negative_prompt=prompt_neg, width=512, height=768, batch_size=2, denoising_strength=0.45, enable_hr=True, hr_second_pass_steps=10, hr_scale=1.5, restore_faces=True, steps=10, seed=-1, sampler_name='DPM++ 2M Karras', )
        return result

