import logging
from pathlib import Path

"""Configures logging for the Autonomous Social Media Multi-Agent application.
Sets up a logger that outputs to both console and a log file with appropriate formatting."""

class config_logger:
 
    LOG_DIR = Path(__file__).resolve().parent.parent/ "logs"
    LOG_DIR.mkdir(exist_ok=True) 

  
    
    def __init__(self,Log_File_Name="SocialMediaMultiAgent.log",Logger_Name="SocialMediaMultiAgent"):  
        self.LOG_FILE = self.LOG_DIR / Log_File_Name
        self.Logger_Name = Logger_Name
        self.logger = logging.getLogger(self.Logger_Name)
        self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%d-%m-%y %H:%M:%S"
        )
        self.setup_handler()
         
    def setup_handler(self):
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.formatter)

        # File handler
        file_handler = logging.FileHandler(self.LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.formatter)

        # Avoid duplicate handlers if logger already configured
        if not self.logger.handlers:
               self.logger.addHandler(console_handler)
               self.logger.addHandler(file_handler)

        return self.logger
    
logger = config_logger().logger
