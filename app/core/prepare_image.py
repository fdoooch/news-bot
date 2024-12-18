from PIL import Image
import os

def convert_and_resize_image(input_path, output_path, size=(800, 600), quality=85):
    """
    Convert an image to JPG format and resize it.
    
    Args:
        input_path (str): Path to input image
        output_path (str): Path to save the converted image
        size (tuple): Desired output size in pixels (width, height)
        quality (int): JPEG quality (1-95, higher is better quality but larger file)
    """
    try:
        # Open the image
        with Image.open(input_path) as img:
            # Convert to RGB if necessary (e.g., if image is RGBA/PNG)
            if img.mode in ('RGBA', 'LA'):
                img = img.convert('RGB')
            
            # Resize the image maintaining aspect ratio
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save as JPEG
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            
        print(f"Successfully converted and resized image: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Single image conversion
    convert_and_resize_image('input_image.png', 'output_image.jpg')
    
    # Process all images in a directory
    def process_directory(input_dir, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(('.png', '.bmp', '.gif', '.webp')):
                input_path = os.path.join(input_dir, filename)
                output_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}.jpg")
                convert_and_resize_image(input_path, output_path)

    # Example directory processing
    # process_directory('input_folder', 'output_folder')