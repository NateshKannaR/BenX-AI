# face_recognition.py

"""
Face Recognition Model

This module provides functionality for face recognition using the face_recognition library.
It allows for the detection of faces in images, extraction of face encodings, and comparison of faces.
"""

import face_recognition
import cv2
import numpy as np
from PIL import Image, ImageDraw

class FaceRecognitionModel:
    """
    Face Recognition Model

    Attributes:
        known_faces (list): List of known face encodings.
        known_face_names (list): List of names corresponding to the known face encodings.
    """

    def __init__(self):
        """
        Initialize the Face Recognition Model.

        Initialize the lists of known face encodings and names.
        """
        self.known_faces = []
        self.known_face_names = []

    def load_known_faces(self, face_encodings, face_names):
        """
        Load known face encodings and names.

        Args:
            face_encodings (list): List of face encodings.
            face_names (list): List of names corresponding to the face encodings.
        """
        self.known_faces = face_encodings
        self.known_face_names = face_names

    def detect_faces(self, image):
        """
        Detect faces in an image.

        Args:
            image (numpy.array): Image to detect faces in.

        Returns:
            list: List of face locations.
        """
        # Convert the image to RGB
        rgb_image = image[:, :, ::-1]

        # Detect faces in the image
        face_locations = face_recognition.face_locations(rgb_image)

        return face_locations

    def extract_face_encodings(self, image, face_locations):
        """
        Extract face encodings from an image.

        Args:
            image (numpy.array): Image to extract face encodings from.
            face_locations (list): List of face locations.

        Returns:
            list: List of face encodings.
        """
        # Convert the image to RGB
        rgb_image = image[:, :, ::-1]

        # Extract face encodings
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

        return face_encodings

    def compare_faces(self, face_encoding, tolerance=0.6):
        """
        Compare a face encoding with the known face encodings.

        Args:
            face_encoding (numpy.array): Face encoding to compare.
            tolerance (float): Tolerance for the comparison. Default is 0.6.

        Returns:
            tuple: Tuple containing a boolean indicating whether a match was found and the name of the match.
        """
        # Compare the face encoding with the known face encodings
        matches = face_recognition.compare_faces(self.known_faces, face_encoding, tolerance)

        # Check if a match was found
        if True in matches:
            # Get the index of the match
            match_index = matches.index(True)

            # Return the name of the match
            return True, self.known_face_names[match_index]
        else:
            # Return False if no match was found
            return False, None

    def recognize_faces(self, image):
        """
        Recognize faces in an image.

        Args:
            image (numpy.array): Image to recognize faces in.

        Returns:
            list: List of tuples containing the face location and name of each recognized face.
        """
        # Detect faces in the image
        face_locations = self.detect_faces(image)

        # Extract face encodings
        face_encodings = self.extract_face_encodings(image, face_locations)

        # Initialize a list to store the recognized faces
        recognized_faces = []

        # Iterate over the face encodings
        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Compare the face encoding with the known face encodings
            match, name = self.compare_faces(face_encoding)

            # If a match was found, add the face location and name to the list of recognized faces
            if match:
                recognized_faces.append((face_location, name))

        return recognized_faces

    def draw_recognized_faces(self, image, recognized_faces):
        """
        Draw the recognized faces on an image.

        Args:
            image (numpy.array): Image to draw the recognized faces on.
            recognized_faces (list): List of tuples containing the face location and name of each recognized face.
        """
        # Convert the image to RGB
        rgb_image = Image.fromarray(image[:, :, ::-1])

        # Create a drawing context
        draw = ImageDraw.Draw(rgb_image)

        # Iterate over the recognized faces
        for face_location, name in recognized_faces:
            # Draw a rectangle around the face
            top, right, bottom, left = face_location
            draw.rectangle((left, top, right, bottom), outline=(0, 0, 255), width=2)

            # Draw the name of the face below the rectangle
            draw.text((left, bottom - 10), name, fill=(0, 0, 255))

        # Return the image with the recognized faces drawn on it
        return np.array(rgb_image)[:, :, ::-1]

def main():
    # Create a Face Recognition Model
    model = FaceRecognitionModel()

    # Load known face encodings and names
    known_face_encodings = [face_recognition.face_encodings(face_recognition.load_image_file("known_faces/face1.jpg"))[0],
                             face_recognition.face_encodings(face_recognition.load_image_file("known_faces/face2.jpg"))[0]]
    known_face_names = ["John Doe", "Jane Doe"]
    model.load_known_faces(known_face_encodings, known_face_names)

    # Load an image to recognize faces in
    image = cv2.imread("image.jpg")

    # Recognize faces in the image
    recognized_faces = model.recognize_faces(image)

    # Draw the recognized faces on the image
    image_with_recognized_faces = model.draw_recognized_faces(image, recognized_faces)

    # Display the image with the recognized faces
    cv2.imshow("Recognized Faces", image_with_recognized_faces)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()