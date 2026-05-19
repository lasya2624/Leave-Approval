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
    # Increasing the vertical height of the signature stamp box significantly.
    # By making the box taller (200 pts) and allowing the boxes to overlap slightly,
    # the auto-cropped signature image can scale to a massive size.
    y_bottom = page.rect.height - 20
    y_top = y_bottom - 200
    
    # Shifted towards the right and massively widened (width 260)
    # Since backgrounds are completely transparent, overlapping bounding boxes are perfectly fine!
    if role == 'MENTOR':
        rect = fitz.Rect(30, y_top, 290, y_bottom)
    elif role == 'HOD':
        rect = fitz.Rect(170, y_top, 430, y_bottom)
    elif role == 'DEAN':
        rect = fitz.Rect(310, y_top, 570, y_bottom)
    else:
        rect = fitz.Rect(30, y_top, 290, y_bottom)
        
    import cv2
    import numpy as np
    
    try:
        # 1. Load the signature image
        img_bgr = cv2.imread(signature_image_path)
        if img_bgr is None:
            raise ValueError(f"Failed to load image: {signature_image_path}")
            
        # 2. Convert to grayscale
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # 3. Estimate Background (Illumination Map)
        # Use a large morphological closing kernel to erase the thin signature strokes,
        # leaving ONLY the background illumination pattern (shadows and gradients).
        bg_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (51, 51))
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, bg_kernel)
        
        # 4. Correct Illumination
        # Divide the original image by the background to equalize brightness across the entire image.
        # Paper (gray/bg = ~1.0 -> 255). Ink (dark/bg = <1.0 -> dark).
        corrected = np.float32(gray) / (np.float32(background) + 1e-5)
        corrected = np.clip(corrected * 255, 0, 255).astype(np.uint8)
        
        # 5. Apply Otsu's thresholding with THRESH_BINARY_INV
        # Now that the background is perfectly uniform, Otsu works flawlessly.
        _, thresh = cv2.threshold(corrected, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 6. Apply morphological operations to clean the final mask
        kernel = np.ones((3, 3), np.uint8)
        
        # Morphological closing (3x3 kernel) to fill gaps inside signature strokes
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Morphological opening (3x3 kernel) to remove small background smudges and shadows
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)
        
        # 6. Split the original BGR channels and merge with the cleaned mask as the alpha channel
        b, g, r = cv2.split(img_bgr)
        rgba = [b, g, r, opened]
        img_rgba = cv2.merge(rgba)
        
        # 6.5. Auto-Crop: Find the bounding box of the ink to remove transparent padding
        # This is CRITICAL to allow PyMuPDF to scale the signature up to the massive 260x200 bounds.
        y_indices, x_indices = np.nonzero(opened)
        if len(y_indices) > 0 and len(x_indices) > 0:
            y_min, y_max = np.min(y_indices), np.max(y_indices)
            x_min, x_max = np.min(x_indices), np.max(x_indices)
            img_rgba = img_rgba[y_min:y_max+1, x_min:x_max+1]
        
        # 7. Encode as PNG with transparency preserved
        success, encoded_img = cv2.imencode('.png', img_rgba)
        if not success:
            raise ValueError("Failed to encode image to PNG format.")
        
        img_bytes = encoded_img.tobytes()
        
        # Insert the processed image stream into the PDF
        page.insert_image(rect, stream=img_bytes)
    except Exception as e:
        # Fallback to original image if processing fails
        print(f"OpenCV Image processing failed: {e}")
        page.insert_image(rect, filename=signature_image_path)
    
    
    # Add a small text label below the signature
    text_point = fitz.Point(rect.x0, y_bottom + 10)
    page.insert_text(text_point, f"Digitally Signed by {role}", fontsize=8, color=(0, 0.5, 0))
    
    doc.save(output_pdf_path)
    doc.close()
    
    return output_pdf_path
