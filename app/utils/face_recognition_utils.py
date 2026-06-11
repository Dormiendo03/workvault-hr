try:
    import face_recognition
    import cv2
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("WARNING: face_recognition not available. Face recognition features will be disabled.")

import numpy as np
import pickle
import os
from flask import current_app
import base64

class FaceRecognitionManager:
    """Manage face recognition operations"""
    
    def __init__(self):
        self.encodings_path = None
        self.known_encodings = {}
        self.available = FACE_RECOGNITION_AVAILABLE
        if self.available:
            self.load_encodings()
        else:
            print("Face recognition is disabled - dlib not installed")
    
    def load_encodings(self):
        """Load all known face encodings from disk"""
        try:
            if current_app:
                self.encodings_path = current_app.config['FACE_ENCODINGS_PATH']
            else:
                self.encodings_path = 'static/faces'
            
            encodings_file = os.path.join(self.encodings_path, 'encodings.pkl')
            
            if os.path.exists(encodings_file):
                with open(encodings_file, 'rb') as f:
                    self.known_encodings = pickle.load(f)
                print(f"Loaded {len(self.known_encodings)} face encodings")
            else:
                self.known_encodings = {}
                print("No existing encodings found, starting fresh")
        except Exception as e:
            print(f"Error loading encodings: {e}")
            self.known_encodings = {}
    
    def save_encodings(self):
        """Save all face encodings to disk"""
        try:
            os.makedirs(self.encodings_path, exist_ok=True)
            encodings_file = os.path.join(self.encodings_path, 'encodings.pkl')
            
            with open(encodings_file, 'wb') as f:
                pickle.dump(self.known_encodings, f)
            
            print(f"Saved {len(self.known_encodings)} face encodings")
            return True
        except Exception as e:
            print(f"Error saving encodings: {e}")
            return False
    
    def enroll_face(self, user_id, image_data):
        """
        Enroll a new face for a user
        image_data: base64 encoded image or file path
        """
        if not self.available:
            return False, "Face recognition is not available. Please install dlib and face_recognition."
        
        try:
            # Decode base64 image if needed
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                # Remove data URL prefix
                image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                
                # Convert to numpy array
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Convert BGR to RGB
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                # Load from file path
                image = face_recognition.load_image_file(image_data)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return False, "No face detected in the image"
            
            if len(face_locations) > 1:
                return False, "Multiple faces detected. Please ensure only one face is visible"
            
            # Get face encoding
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if len(face_encodings) == 0:
                return False, "Could not encode face"
            
            # Store encoding
            self.known_encodings[str(user_id)] = face_encodings[0]
            
            # Save to disk
            if self.save_encodings():
                return True, "Face enrolled successfully"
            else:
                return False, "Failed to save face encoding"
            
        except Exception as e:
            print(f"Error enrolling face: {e}")
            return False, f"Error: {str(e)}"
    
    def verify_face(self, image_data, tolerance=0.6):
        """
        Verify a face against all known encodings
        Returns (user_id, confidence) or (None, None) if no match
        """
        if not self.available:
            return None, None, "Face recognition is not available. Please install dlib and face_recognition."
        
        try:
            # Decode base64 image
            if isinstance(image_data, str) and image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image = face_recognition.load_image_file(image_data)
            
            # Find faces
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return None, None, "No face detected"
            
            if len(face_locations) > 1:
                return None, None, "Multiple faces detected"
            
            # Get encoding
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            if len(face_encodings) == 0:
                return None, None, "Could not encode face"
            
            unknown_encoding = face_encodings[0]
            
            # Compare with known faces
            if not self.known_encodings:
                return None, None, "No enrolled faces in system"
            
            known_ids = list(self.known_encodings.keys())
            known_encodings_list = list(self.known_encodings.values())
            
            # Calculate face distances
            face_distances = face_recognition.face_distance(known_encodings_list, unknown_encoding)
            
            # Find best match
            best_match_index = np.argmin(face_distances)
            best_distance = face_distances[best_match_index]
            
            if best_distance <= tolerance:
                user_id = known_ids[best_match_index]
                confidence = 1 - best_distance  # Convert distance to confidence
                return user_id, confidence, None
            
            return None, None, "No matching face found"
            
        except Exception as e:
            print(f"Error verifying face: {e}")
            return None, None, f"Error: {str(e)}"
    
    def delete_face(self, user_id):
        """Delete a user's face encoding"""
        try:
            user_id_str = str(user_id)
            if user_id_str in self.known_encodings:
                del self.known_encodings[user_id_str]
                self.save_encodings()
                return True, "Face encoding deleted"
            return False, "No face encoding found for this user"
        except Exception as e:
            print(f"Error deleting face: {e}")
            return False, f"Error: {str(e)}"
    
    def has_enrollment(self, user_id):
        """Check if a user has an enrolled face"""
        return str(user_id) in self.known_encodings

# Global instance
face_manager = FaceRecognitionManager()
