import hashlib
import os
import io
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def generate_rsa_keypair():
    """
    Generate RSA key pair for Digital Signature.
    NOTE FOR USER: Replace this logic with your custom RSA algorithm if needed.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_pem, public_pem

def generate_verification_key(unique_string: str) -> str:
    """
    Generate SHA-256 hash for document verification.
    NOTE FOR USER: Replace this with your custom SHA-256 algorithm if needed.
    """
    sha_signature = hashlib.sha256(unique_string.encode()).hexdigest()
    return sha_signature

def visually_sign_pdf(input_pdf_path, output_pdf_path, signature_image_path, role):
    """
    Places the visual signature image on the PDF using PyMuPDF.
    """
    import fitz
    
    doc = fitz.open(input_pdf_path)
    page = doc[-1] # Put signature on the last page
    
    # Calculate position based on role
    y_bottom = page.rect.height - 50
    y_top = y_bottom - 60
    
    if role == 'MENTOR':
        rect = fitz.Rect(50, y_top, 200, y_bottom)
    elif role == 'HOD':
        rect = fitz.Rect(230, y_top, 380, y_bottom)
    elif role == 'DEAN':
        rect = fitz.Rect(410, y_top, 560, y_bottom)
    else:
        rect = fitz.Rect(50, y_top, 200, y_bottom)
        
    from PIL import Image
    import io
    
    # Process the signature image to extract only the ink (make background transparent)
    try:
        img = Image.open(signature_image_path).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            # Calculate luminance to determine if pixel is dark (ink) or light (background)
            luminance = item[0]*0.299 + item[1]*0.587 + item[2]*0.114
            if luminance > 180: # Background
                newData.append((255, 255, 255, 0)) # Transparent
            else:
                # Keep the ink but ensure it is fully opaque
                newData.append((item[0], item[1], item[2], 255))
        img.putdata(newData)
        
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # Insert the processed image stream
        page.insert_image(rect, stream=img_bytes)
    except Exception as e:
        # Fallback to original image if processing fails
        print(f"Image processing failed: {e}")
        page.insert_image(rect, filename=signature_image_path)
    
    
    # Add a small text label below the signature
    text_point = fitz.Point(rect.x0, y_bottom + 10)
    page.insert_text(text_point, f"Digitally Signed by {role}", fontsize=8, color=(0, 0.5, 0))
    
    doc.save(output_pdf_path)
    doc.close()
    
    return output_pdf_path
