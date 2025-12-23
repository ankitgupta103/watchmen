import math
import re

def dms_to_decimal(dms):
    # dms = Degrees, Minutes, Seconds format (e.g., "34°09'25.7"N")
    # Parse the DMS string to extract degrees, minutes, seconds, and direction
    m = re.match(r"(\d+)°(\d+)'([\d.]+)\"([NSEW])", dms)
    # Convert to decimal degrees: degrees + minutes/60 + seconds/3600
    d = int(m.group(1)) + int(m.group(2))/60 + float(m.group(3))/3600
    # Make negative if South or West direction
    return -d if m.group(4) in 'SW' else d

def distance(lat1, lon1, lat2, lon2):
    # R = Earth's radius in meters (6371 km = 6371000 meters)
    R = 6371000
    # Convert latitude and longitude differences to radians
    dlat = math.radians(lat2 - lat1)  # Difference in latitude
    dlon = math.radians(lon2 - lon1)  # Difference in longitude
    # Haversine formula: calculates distance between two points on a sphere
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    # Return distance in meters
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Read coordinates from file and convert to decimal degrees
points = []
with open('lat-long.txt', 'r') as f:
    for line in f:
        if ':' in line:
            # Extract latitude and longitude strings from each line
            lat_str, lon_str = line.split(':')[1].strip().split()
            # Convert DMS to decimal and store as (latitude, longitude) tuple
            points.append((dms_to_decimal(lat_str), dms_to_decimal(lon_str)))

# Calculate and print distance between all pairs of points
for i in range(len(points)):
    for j in range(i+1, len(points)):  # j > i to avoid duplicate pairs
        d = distance(points[i][0], points[i][1], points[j][0], points[j][1])  # Calculate distance in meters
        print(f"Point {i+1} to Point {j+1}: {d:.2f} meters")
