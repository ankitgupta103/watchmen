import os
import sys
from PIL import Image
from collections import defaultdict
import re
from datetime import datetime

def im2bytes(fname):
    """Convert image to grayscale bytes and return metadata"""
    try:
        img = Image.open(fname)
        img = img.convert("L")
        width, height = img.size
        pixel_bytes = img.tobytes()
        
        return {
            'bytes': pixel_bytes,
            'width': width,
            'height': height,
            'byte_length': len(pixel_bytes)
        }
    except Exception as e:
        print(f"Error processing {fname}: {e}")
        return None

def diff_ims(f1, f2):
    """Compare two images and return difference percentage"""
    print(f"\nComparing reference vs {os.path.basename(f2)}")
    
    data1 = im2bytes(f1)
    data2 = im2bytes(f2)
    
    if not data1 or not data2:
        return None
    
    b1, b2 = data1['bytes'], data2['bytes']
    
    print(f"Reference - Width: {data1['width']}, Height: {data1['height']}, Bytes: {data1['byte_length']}")
    print(f"Compare   - Width: {data2['width']}, Height: {data2['height']}, Bytes: {data2['byte_length']}")
    
    if len(b1) != len(b2):
        print("Size mismatch")
        return None
    
    # Calculate differences
    d = []
    for x in range(len(b1)):
        d.append(abs(b2[x] - b1[x]))
    
    num_diff = sum(1 for x in d if x > 32)
    d32 = float(num_diff * 100 / len(b1))
    
    print(f"Pixels with >32 difference: {num_diff}/{len(b1)} ({d32:.2f}%)")
    
    return d32

def extract_location_id(filename):
    """Extract location ID from filename"""
    # Pattern for LOC_006-xxxxx-xx.jpg or LOC_548523-xxxxxxxxxx-xxxx.jpg
    match = re.match(r'LOC_(\d+)-', filename)
    if match:
        return match.group(1)
    return None

def group_images_by_location(image_directory):
    """Group images by their location ID"""
    location_groups = defaultdict(list)
    
    # Get all jpg files in directory
    image_files = [f for f in os.listdir(image_directory) if f.lower().endswith('.jpg')]
    
    for filename in image_files:
        location_id = extract_location_id(filename)
        if location_id:
            full_path = os.path.join(image_directory, filename)
            location_groups[location_id].append(full_path)
        else:
            print(f"Warning: Could not extract location ID from {filename}")
    
    return location_groups

def find_reference_image(reference_name, image_files):
    """Find the reference image in the list of files"""
    for img_path in image_files:
        if os.path.basename(img_path) == reference_name:
            return img_path
    return None

def rename_images_in_directory(image_results, location_id, output_file):
    """Rename image files in directory to maintain sorted order"""
    print(f"\nRenaming images in directory to maintain sorted order...")
    output_file.write(f"\nFile renaming operations:\n")
    output_file.write("-" * 50 + "\n")
    
    renamed_files = []
    
    for i, result in enumerate(image_results, 1):
        if result.get('error'):
            continue
            
        old_path = result['path']
        old_name = result['name']
        directory = os.path.dirname(old_path)
        
        # Create new filename with order prefix and diff percentage
        name_without_ext = os.path.splitext(old_name)[0]
        extension = os.path.splitext(old_name)[1]
        
        if result.get('is_reference'):
            new_name = f"{i:03d}_REF_{name_without_ext}_diff_0.00%{extension}"
        else:
            new_name = f"{i:03d}_{name_without_ext}_diff_{result['diff']:.2f}%{extension}"
        
        new_path = os.path.join(directory, new_name)
        
        try:
            os.rename(old_path, new_path)
            rename_msg = f"Renamed: {old_name} -> {new_name}"
            print(f"  {rename_msg}")
            output_file.write(f"{rename_msg}\n")
            
            renamed_files.append({
                'old_name': old_name,
                'new_name': new_name,
                'diff': result['diff'],
                'order': i
            })
            
        except Exception as e:
            error_msg = f"Error renaming {old_name}: {e}"
            print(f"  {error_msg}")
            output_file.write(f"{error_msg}\n")
    
    return renamed_files

def process_location_group(location_id, image_files, reference_name, output_file):
    """Process all images in a location group against reference image and record results"""
    print(f"\n{'='*60}")
    print(f"Processing Location ID: {location_id}")
    print(f"Reference image: {reference_name}")
    print(f"Number of images: {len(image_files)}")
    print(f"{'='*60}")
    
    # Find reference image
    reference_path = find_reference_image(reference_name, image_files)
    if not reference_path:
        error_msg = f"Reference image '{reference_name}' not found in location {location_id}"
        print(f"Error: {error_msg}")
        output_file.write(f"\nLocation {location_id}: ERROR - {error_msg}\n")
        return
    
    # Write location header to output file
    output_file.write(f"\n{'='*60}\n")
    output_file.write(f"Location ID: {location_id}\n")
    output_file.write(f"Reference image: {reference_name}\n")
    output_file.write(f"Number of images: {len(image_files)}\n")
    output_file.write(f"Processing time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    output_file.write(f"{'='*60}\n")
    
    # Compare all images against reference
    image_results = []
    
    for img_path in image_files:
        img_name = os.path.basename(img_path)
        
        if img_name == reference_name:
            # Reference image has 0% difference with itself
            image_results.append({
                'name': img_name,
                'path': img_path,
                'diff': 0.0,
                'is_reference': True
            })
        else:
            diff_ratio = diff_ims(reference_path, img_path)
            
            if diff_ratio is not None:
                image_results.append({
                    'name': img_name,
                    'path': img_path,
                    'diff': diff_ratio,
                    'is_reference': False
                })
            else:
                image_results.append({
                    'name': img_name,
                    'path': img_path,
                    'diff': float('inf'),  # Use infinity for failed comparisons
                    'is_reference': False,
                    'error': True
                })
    
    # Sort by difference percentage (ascending order)
    image_results.sort(key=lambda x: x['diff'])
    
    # Write sorted results (before renaming)
    output_file.write(f"\nOriginal images sorted by difference from reference (ascending order):\n")
    output_file.write("-" * 70 + "\n")
    
    for i, result in enumerate(image_results, 1):
        if result.get('is_reference'):
            line = f"{i:2d}. {result['name']} [REFERENCE] - 0.00% diff"
        elif result.get('error'):
            line = f"{i:2d}. {result['name']} - ERROR (size mismatch or processing error)"
        else:
            line = f"{i:2d}. {result['name']} - {result['diff']:.2f}% diff"
        
        print(line)
        output_file.write(line + "\n")
    
    # Rename files in directory to maintain sorted order
    renamed_files = rename_images_in_directory(image_results, location_id, output_file)
    
    # Write final sorted filenames after renaming
    output_file.write(f"\nFinal sorted filenames in directory:\n")
    output_file.write("-" * 50 + "\n")
    
    for renamed_file in renamed_files:
        line = f"{renamed_file['order']:2d}. {renamed_file['new_name']}"
        output_file.write(line + "\n")
    
    # Summary for this location
    valid_comparisons = [r for r in image_results if not r.get('error') and not r.get('is_reference')]
    if valid_comparisons:
        min_diff = min(r['diff'] for r in valid_comparisons)
        max_diff = max(r['diff'] for r in valid_comparisons)
        avg_diff = sum(r['diff'] for r in valid_comparisons) / len(valid_comparisons)
        significant_diffs = sum(1 for r in valid_comparisons if r['diff'] > 2.0)
    else:
        min_diff = max_diff = avg_diff = 0
        significant_diffs = 0
    
    summary = f"""
Location {location_id} Summary:
- Reference image: {reference_name}
- Total images compared: {len(image_results)}
- Valid comparisons: {len(valid_comparisons)}
- Files successfully renamed: {len(renamed_files)}
- Minimum difference: {min_diff:.2f}%
- Maximum difference: {max_diff:.2f}%
- Average difference: {avg_diff:.2f}%
- Images with >2% difference: {significant_diffs}

"""
    print(summary)
    output_file.write(summary)
    output_file.flush()

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <image_directory> <reference_image_name>")
        print("Example: python script.py /path/to/images/ LOC_006-10116-28.jpg")
        sys.exit(1)
    
    image_directory = sys.argv[1]
    reference_name = sys.argv[2]
    
    if not os.path.isdir(image_directory):
        print(f"Error: {image_directory} is not a valid directory")
        sys.exit(1)
    
    # Extract location ID from reference image
    reference_location = extract_location_id(reference_name)
    if not reference_location:
        print(f"Error: Could not extract location ID from reference image '{reference_name}'")
        print("Make sure the filename follows the pattern LOC_XXXXXX-...")
        sys.exit(1)
    
    # Group images by location
    location_groups = group_images_by_location(image_directory)
    
    if not location_groups:
        print("No images with valid location IDs found!")
        sys.exit(1)
    
    # Check if reference location exists
    if reference_location not in location_groups:
        print(f"Error: No images found for location '{reference_location}'")
        print(f"Available locations: {', '.join(sorted(location_groups.keys()))}")
        sys.exit(1)
    
    # Create output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"location_analysis_{reference_location}_{timestamp}.txt"
    
    print(f"Processing location: {reference_location}")
    print(f"Reference image: {reference_name}")
    print(f"Found {len(location_groups[reference_location])} images in this location")
    print(f"Results will be saved to: {output_filename}")
    
    with open(output_filename, 'w') as output_file:
        # Write header
        output_file.write(f"Image Location Analysis Report\n")
        output_file.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output_file.write(f"Source directory: {image_directory}\n")
        output_file.write(f"Target location: {reference_location}\n")
        output_file.write(f"Reference image: {reference_name}\n")
        
        # Process the specific location
        image_files = location_groups[reference_location]
        process_location_group(reference_location, image_files, reference_name, output_file)
        
        # Write final summary
        final_summary = f"""
{'='*60}
ANALYSIS COMPLETE
{'='*60}
Location processed: {reference_location}
Reference image: {reference_name}
Total images in location: {len(image_files)}
Analysis complete: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        print(final_summary)
        output_file.write(final_summary)
    
    print(f"\nAnalysis complete! Results saved to {output_filename}")

if __name__ == "__main__":
    main()