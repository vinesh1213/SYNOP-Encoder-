import os
import glob
from apscheduler.schedulers.background import BackgroundScheduler
from config.settings import load_config
from decoders.synop_decoder import SynopDecoder
from database.db import get_db

class AutoDecoderService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.decoder = SynopDecoder()
        self.config = load_config()
        self.input_folder = self.config.get("auto_decoder", {}).get("input_folder", "./incoming_synops")
        self.output_folder = self.config.get("auto_decoder", {}).get("output_folder", "./decoded_synops")
        self.interval = self.config.get("auto_decoder", {}).get("interval_seconds", 60)
        
        # Ensure folders exist
        os.makedirs(self.input_folder, exist_ok=True)
        os.makedirs(self.output_folder, exist_ok=True)

    def process_incoming_files(self):
        """Scans the input folder for .txt files, decodes them, and moves them to output folder."""
        # Refresh config in case it changed
        self.config = load_config()
        if not self.config.get("auto_decoder", {}).get("enabled", True):
            return
            
        txt_files = glob.glob(os.path.join(self.input_folder, "*.txt"))
        
        for file_path in txt_files:
            filename = os.path.basename(file_path)
            
            # Decode file
            results = self.decoder.decode_file(file_path)
            
            # Here you would typically save results to database
            # For demonstration, we print to console and assume success
            print(f"Auto-Decoder: Processed {filename}, found {len(results)} potential SYNOP lines.")
            
            # Move file to output folder (or rename with processed extension)
            output_path = os.path.join(self.output_folder, filename)
            try:
                # Replace if exists
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(file_path, output_path)
            except Exception as e:
                print(f"Failed to move {file_path} to {output_path}: {e}")

    def start(self):
        self.scheduler.add_job(self.process_incoming_files, 'interval', seconds=self.interval, id='auto_decoder_job', replace_existing=True)
        self.scheduler.start()
        
    def stop(self):
        self.scheduler.shutdown()

    def update_interval(self, new_interval: int):
        self.interval = new_interval
        self.scheduler.reschedule_job('auto_decoder_job', trigger='interval', seconds=self.interval)

# Singleton instance to be used by FastAPI startup events
auto_decoder_service = AutoDecoderService()
