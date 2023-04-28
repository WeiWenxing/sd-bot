import logging

from transformers import AutoProcessor, CLIPSegProcessor, CLIPSegForImageSegmentation
import gradio as gr
from PIL import ImageChops, Image, ImageOps
import torch
import matplotlib.pyplot as plt
import cv2
import numpy



# processor = AutoProcessor.from_pretrained("CIDAS/clipseg-rd64-refined")
processor = CLIPSegProcessor.from_pretrained("CIDAS/clipseg-rd64-refined")
model = CLIPSegForImageSegmentation.from_pretrained("CIDAS/clipseg-rd64-refined")


def gray_to_pil(img):
    return (Image.fromarray(cv2.cvtColor(img,cv2.COLOR_GRAY2RGBA)))


def center_crop(img,new_width,new_height):
    width, height = img.size   # Get dimensions

    left = (width - new_width)/2
    top = (height - new_height)/2
    right = (width + new_width)/2
    bottom = (height + new_height)/2

    # Crop the center of the image
    return(img.crop((left, top, right, bottom)))


def overlay_mask_part(img_a,img_b,mode):
    if (mode == 0):
        img_a = ImageChops.darker(img_a, img_b)
    else: img_a = ImageChops.lighter(img_a, img_b)
    return(img_a)


def run(image, mask_prompt, negative_mask_prompt, mask_precision, mask_padding=4):
    def process_mask_parts(these_preds,these_prompt_parts,mode,final_img = None):
        for i in range(these_prompt_parts):
            filename = f"mask_{mode}_{i}.png"
            plt.imsave(filename,torch.sigmoid(these_preds[i]))

            # TODO: Figure out how to convert the plot above to numpy instead of re-loading image
            img = cv2.imread(filename)
            gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            (thresh, bw_image) = cv2.threshold(gray_image, mask_precision, 255, cv2.THRESH_BINARY)

            if (mode == 0): bw_image = numpy.invert(bw_image)

            # overlay mask parts
            bw_image = gray_to_pil(bw_image)
            if (i > 0 or final_img is not None):
                bw_image = overlay_mask_part(bw_image,final_img,mode)

            final_img = bw_image

            return(final_img)

    def get_mask():
        delimiter_string = "|"

        prompts = mask_prompt.split(delimiter_string)
        prompt_parts = len(prompts)
        negative_prompts = negative_mask_prompt.split(delimiter_string)
        negative_prompt_parts = len(negative_prompts)

        inputs = processor(text=prompts, images=[image] * prompt_parts, padding="max_length", return_tensors="pt")
        negative_inputs = processor(text=negative_prompts, images=[image] * negative_prompt_parts, padding="max_length", return_tensors="pt")
        with torch.no_grad():
            preds = model(**inputs).logits
            negative_preds = model(**negative_inputs).logits

        final_img = None

        # process masking
        final_img = process_mask_parts(preds,prompt_parts,1,final_img)
        # process negative masking
        if (negative_mask_prompt): final_img = process_mask_parts(negative_preds,negative_prompt_parts,0,final_img)

        width, height = image.size
        aspect_ratio = width / height
        new_width = width+mask_padding*2
        new_height = round(new_width / aspect_ratio)
        final_img = final_img.resize((new_width, new_height))
        final_img = center_crop(final_img, width, height)

        return (final_img)

        # logging.info(preds.shape)
        # filename = f"mask.png"
        # plt.imsave(filename, torch.sigmoid(preds[0]))
        # return Image.open(filename)

    image_mask = get_mask().resize(image.size)
    return image_mask
