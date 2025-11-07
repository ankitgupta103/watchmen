import sys
from PIL import Image
import io

def im2bytes(fname):
    img = Image.open(fname)
    img = img.convert("L")
    width, height = img.size
    print(f"Image width: {width} pixels")
    print(f"Image height: {height} pixels")
    pixel_bytes = img.tobytes()
    print(f"Pillow bytelen = {len(pixel_bytes)} : Min:{min(pixel_bytes)}, Max:{max(pixel_bytes)}")
    return pixel_bytes

def diff_ims(f1, f2):
    b1 = im2bytes(f1)
    b2 = im2bytes(f2)
    print(len(b1))
    print(len(b2))
    if len(b1) != len(b2):
        print("Size mismatch")
        return None
    d = []
    db = b''
    for x in range(len(b1)):
        di = abs(b2[x] - b1[x])
        d.append(di)
        db += di.to_bytes(1)
    d_image = Image.frombytes("L", (1280,720), db)
    d_image.show()

    num_diff = 0
    for x in d:
        if x > 32:
            num_diff += 1
    d32 = float(num_diff*100/len(b1))
    print(f"Num of more than 32 diffs is {d32}")
    return d32

def main():
    ratio = diff_ims(sys.argv[1], sys.argv[2])
    print(f"Diff : {ratio>2.0}")

if __name__ == "__main__":
    main()
