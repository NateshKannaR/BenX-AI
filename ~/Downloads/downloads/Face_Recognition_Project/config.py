# Project Configuration File
# This file contains all the configuration settings for the project.

import os

class Config:
    """
    Base configuration class.
    """
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'secret_key_here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    """
    Development configuration class.
    """
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    """
    Production configuration class.
    """
    DEBUG = False
    SQLALCHEMY_ECHO = False

class TestingConfig(Config):
    """
    Testing configuration class.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_database.db'

# Dictionary mapping configuration names to their respective classes
config_dict = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}