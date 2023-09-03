from torchvision import transforms
from io import BytesIO
from PIL import Image
from PIL.ImageOps import exif_transpose
import logging, os

logger = logging.getLogger("MultiaspectImage")
logger.setLevel(os.environ.get("SIMPLETUNER_LOG_LEVEL", "WARNING"))


class MultiaspectImage:
    @staticmethod
    def get_image_transforms():
        return transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize([0.5], [0.5]),
            ]
        )

    @staticmethod
    def process_for_bucket(
        data_backend,
        image_path_str,
        aspect_ratio_bucket_indices,
        aspect_ratio_rounding: int = 2,
    ):
        try:
            image_data = data_backend.read(image_path_str)
            with Image.open(BytesIO(image_data)) as image:
                # Apply EXIF transforms
                image = exif_transpose(image)
                # Round to avoid excessive unique buckets
                aspect_ratio = round(image.width / image.height, aspect_ratio_rounding)
                logger.debug(
                    f"Image {image_path_str} has aspect ratio {aspect_ratio} and size {image.size}."
                )
            # Create a new bucket if it doesn't exist
            if str(aspect_ratio) not in aspect_ratio_bucket_indices:
                aspect_ratio_bucket_indices[str(aspect_ratio)] = []
            aspect_ratio_bucket_indices[str(aspect_ratio)].append(image_path_str)
        except Exception as e:
            logger.error(f"Error processing image {image_path_str}.")
            logger.error(e)
        return aspect_ratio_bucket_indices

    @staticmethod
    def prepare_image(image: Image, resolution: int):
        # Strip transparency
        image = image.convert("RGB")
        # Rotate, maybe.
        image = exif_transpose(image)
        image = MultiaspectImage.resize_for_condition_image(image, resolution)
        return image

    @staticmethod
    def resize_for_condition_image(input_image: Image, resolution: int):
        input_image = input_image.convert("RGB")
        W, H = input_image.size
        aspect_ratio = round(W / H, 2)
        msg = f"Resizing image of aspect {aspect_ratio} and size {W}x{H} to its new size: "
        if W < H:
            W = resolution
            H = int(resolution / aspect_ratio)  # Calculate the new height
        elif H < W:
            H = resolution
            W = int(resolution * aspect_ratio)  # Calculate the new width
        if W == H:
            W = resolution
            H = resolution
        if (W, H) == input_image.size:
            return input_image
        msg = f"{msg} {W}x{H}."
        logger.debug(msg)
        img = input_image.resize((W, H), resample=Image.BICUBIC)
        return img
