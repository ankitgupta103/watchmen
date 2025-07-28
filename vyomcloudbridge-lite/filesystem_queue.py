import json
import os
import time
import gc

class FilesystemQueue:
    """
    MicroPython-compatible filesystem-backed queue implementation
    Replaces RabbitMQ functionality with simple file-based storage
    """
    
    def __init__(self, queue_dir="/queue", max_size=100):
        self.queue_dir = queue_dir
        self.max_size = max_size
        self.message_counter = 0
        
        # Create queue directory if it doesn't exist
        try:
            os.makedirs(self.queue_dir)
        except OSError:
            pass  # Directory already exists
    
    def _get_message_filename(self):
        """Generate unique filename for message"""
        timestamp = int(time.time() * 1000)
        self.message_counter += 1
        return f"msg_{timestamp}_{self.message_counter}.json"
    
    def _cleanup_old_messages(self):
        """Remove old messages if queue exceeds max_size"""
        try:
            files = os.listdir(self.queue_dir)
            json_files = [f for f in files if f.endswith('.json')]
            
            if len(json_files) >= self.max_size:
                # Sort by creation time (embedded in filename)
                json_files.sort()
                # Remove oldest files
                to_remove = len(json_files) - self.max_size + 1
                for i in range(to_remove):
                    try:
                        os.remove(os.path.join(self.queue_dir, json_files[i]))
                    except OSError:
                        pass
        except OSError:
            pass
    
    def enqueue(self, message, topic="default"):
        """Add message to queue"""
        try:
            self._cleanup_old_messages()
            
            filename = self._get_message_filename()
            filepath = os.path.join(self.queue_dir, filename)
            
            queue_item = {
                "message": message,
                "topic": topic,
                "timestamp": int(time.time() * 1000),
                "attempts": 0
            }
            
            with open(filepath, 'w') as f:
                json.dump(queue_item, f)
            
            # Force garbage collection for memory management
            gc.collect()
            return True
            
        except Exception as e:
            print(f"Error enqueuing message: {e}")
            return False
    
    def dequeue(self):
        """Remove and return oldest message from queue"""
        try:
            files = os.listdir(self.queue_dir)
            json_files = [f for f in files if f.endswith('.json')]
            
            if not json_files:
                return None
            
            # Get oldest file
            json_files.sort()
            oldest_file = json_files[0]
            filepath = os.path.join(self.queue_dir, oldest_file)
            
            # Read message
            with open(filepath, 'r') as f:
                queue_item = json.load(f)
            
            # Remove file
            os.remove(filepath)
            
            gc.collect()
            return queue_item
            
        except Exception as e:
            print(f"Error dequeuing message: {e}")
            return None
    
    def peek(self):
        """Return oldest message without removing it"""
        try:
            files = os.listdir(self.queue_dir)
            json_files = [f for f in files if f.endswith('.json')]
            
            if not json_files:
                return None
            
            # Get oldest file
            json_files.sort()
            oldest_file = json_files[0]
            filepath = os.path.join(self.queue_dir, oldest_file)
            
            with open(filepath, 'r') as f:
                queue_item = json.load(f)
            
            return queue_item
            
        except Exception as e:
            print(f"Error peeking message: {e}")
            return None
    
    def size(self):
        """Return number of messages in queue"""
        try:
            files = os.listdir(self.queue_dir)
            return len([f for f in files if f.endswith('.json')])
        except OSError:
            return 0
    
    def clear(self):
        """Remove all messages from queue"""
        try:
            files = os.listdir(self.queue_dir)
            for file in files:
                if file.endswith('.json'):
                    os.remove(os.path.join(self.queue_dir, file))
            gc.collect()
            return True
        except Exception as e:
            print(f"Error clearing queue: {e}")
            return False
    
    def mark_failed(self, queue_item, max_attempts=3):
        """Mark message as failed and optionally re-queue"""
        try:
            queue_item["attempts"] += 1
            
            if queue_item["attempts"] < max_attempts:
                # Re-queue with updated attempt count
                filename = self._get_message_filename()
                filepath = os.path.join(self.queue_dir, filename)
                
                with open(filepath, 'w') as f:
                    json.dump(queue_item, f)
                
                return True
            else:
                # Move to failed directory or log
                print(f"Message failed after {max_attempts} attempts: {queue_item}")
                return False
                
        except Exception as e:
            print(f"Error marking message as failed: {e}")
            return False