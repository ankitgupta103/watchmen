import io
import base64
from PIL import Image

def image2string(imagefile):
    r""" Convert Pillow image to string. """
    image = Image.open(imagefile)
    # image.show()
    image = image.convert('RGB')
    img_bytes_arr = io.BytesIO()
    image.save(img_bytes_arr, format="JPEG")
    img_bytes_arr.seek(0)
    img_bytes_arr = img_bytes_arr.read()
    img_bytes_arr_encoded = base64.b64encode(img_bytes_arr)
    res = img_bytes_arr_encoded.decode('utf-8')
    return res

def imstrtoimage(string: str) -> Image.Image:
    r""" Convert string to Pillow image. """
    img_bytes_arr = string.encode('utf-8')
    img_bytes_arr_encoded = base64.b64decode(img_bytes_arr)
    image = Image.open(io.BytesIO(img_bytes_arr_encoded))
    return image

def imstrtobytes(string: str) -> bytes:
    """Convert base64 string to image bytes."""
    return base64.b64decode(string.encode('utf-8'))