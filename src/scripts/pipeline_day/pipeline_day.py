import sys
from src.scripts.pipeline_day.transform.preprocesssor import main_pipeline_day
from src.scripts.pipeline_day.transform.featureengineer import main_feature_engineering_day
from src.scripts.pipeline_day.extract.extract_day import extract_day_data
# from src.scripts.load.to_dir import load_clean_data_to_dir
from src.scripts.pipeline_day.load.to_minio import load_clean_data_to_minio
from datetime import datetime, timedelta
from src.scripts.utils import common as utils
from loguru import logger


def main_pipeline_by_day(date: str):
    """
    Xử lý dữ liệu theo ngày,
    xuất ra file parquet dữ liệu được xử lý
    """
    day_data = extract_day_data(date)

    day_data = main_pipeline_day(day_data)
    
    day_data = main_feature_engineering_day(day_data)

    # load_clean_data_to_dir(date, day_data)
    load_clean_data_to_minio(folder_name="hitech_day", date=date, data=day_data)
    print(f"Pipeline day data completed for {date}")
    
    return day_data

# Chạy pipeline
if __name__ == "__main__":
    # get arguments
    args_string = " ".join(sys.argv[1:])
    args = utils.process_args_to_dict(args_string)
    logger.info("Parsed ARGS in run_create_feature: %s", args)
    start_date = args["dt_from"]
    end_date = args["dt_to"]
    start_date = datetime.strptime(start_date, "%Y%m%d")
    end_date = datetime.strptime(end_date, "%Y%m%d")

    logger.info(f"Start pipeline day from {start_date} to {end_date}")
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y%m%d")
        main_pipeline_by_day(date_str)
        current_date += timedelta(days=1)