def get_suspicious_event_details(detected_objects, confidence_scores):
    """
    Determine suspicious event type and severity based on detection results
    
    Returns:
        dict: Event details with type, severity, and description
    """
    if not detected_objects:
        return {
            "type": "unusual_activity",  
            "severity": "low",
            "description": "Image processed - no specific threats detected"
        }
    
    max_confidence = max(confidence_scores) if confidence_scores else 0
    
    # Check for weapon detection
    weapon_items = ["knife", "scissors", "gun", "baseball bat"]
    human_items = ["person"]
    
    for obj in detected_objects:
        if obj in weapon_items:
            severity = "critical" if max_confidence > 0.8 else "high"
            return {
                "type": "weapon_detection",
                "severity": severity,
                "description": f"Weapon detected: {obj} with {max_confidence:.2f} confidence"
            }
        elif obj in human_items:
            severity = "high" if max_confidence > 0.7 else "medium"
            return {
                "type": "human_detection", 
                "severity": severity,
                "description": f"Human detected with {max_confidence:.2f} confidence"
            }
    
    # Other objects detected
    severity = "medium" if max_confidence > 0.5 else "low"
    return {
        "type": "unusual_activity",
        "severity": severity,
        "description": f"Objects detected: {', '.join(detected_objects)}"
    }

def get_health_event_priority(severity):
    """Get priority level for health events based on severity"""
    return 3 if severity in ["high", "critical"] else 1

def get_suspicious_event_priority(severity):
    """Get priority level for suspicious events based on severity"""
    return 3 if severity in ["high", "critical"] else 2

def extract_detection_from_filename(cropped_filename):
    """
    Extract object type and confidence from cropped image filename
    
    Args:
        cropped_filename: Filename like "image_person_1_conf0.85_cropped.jpg"
        
    Returns:
        tuple: (detected_objects_list, confidence_float)
    """
    detected_objects = []
    confidence = 0.85
    
    if "_cropped.jpg" in cropped_filename:
        parts = cropped_filename.replace("_cropped.jpg", "").split("_")
        if len(parts) >= 3:
            detected_objects = [parts[-2]]  # Object type
            try:
                confidence = float(parts[-1].replace("conf", ""))
            except:
                confidence = 0.85
                
    return detected_objects, confidence