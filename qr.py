import qrcode
import os

# Dashboard URL
url = "http://10.165.141.186:5005"

print(f"Generating QR code for: {url}")

# Create QR code object with custom settings
qr = qrcode.QRCode(
    version=1,          # Controls max capacity (1-40)
    box_size=10,        # Pixels per box
    border=5,           # Border thickness
)
qr.add_data(url)
qr.make(fit=True)

# Generate and save image
img = qr.make_image(fill_color="black", back_color="white")
img.save("comfortsense_qr.png")

print("QR code saved as 'comfortsense_qr.png'!")
print(f"Saved to: {os.path.abspath('comfortsense_qr.png')}")

